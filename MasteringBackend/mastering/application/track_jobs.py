import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Literal

from mastering.stems.rebalance_master import process_rebalance_master
from mastering.stems.stem_lab import _run_demucs

TrackStatus = Literal["uploaded", "separating", "ready_to_mix", "rendering", "done", "failed"]
STEM_NAMES = ("vocals", "drums", "bass", "other")


@dataclass
class TrackRecord:
    track_id: str
    status: TrackStatus
    original_path: str
    work_dir: str
    model: str = "mdx_extra"
    stems_dir: str | None = None
    output_path: str | None = None
    report_path: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class RenderParams:
    profile: str
    mastering_preset: str
    controls: dict[str, float]
    skip_final_master: bool = False


class TrackJobService:
    def __init__(self, root_dir: Path, max_workers: int = 1) -> None:
        self.root_dir = root_dir.resolve()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tracks: dict[str, TrackRecord] = {}

    def create_track(
        self,
        file_obj: BinaryIO,
        filename: str | None,
        model: str = "mdx_extra",
    ) -> TrackRecord:
        track_id = uuid.uuid4().hex
        work_dir = self.root_dir / track_id
        work_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(filename or "input.wav").suffix or ".wav"
        original_path = work_dir / f"original{suffix}"
        with original_path.open("wb") as handle:
            shutil.copyfileobj(file_obj, handle)

        record = TrackRecord(
            track_id=track_id,
            status="uploaded",
            original_path=str(original_path),
            work_dir=str(work_dir),
            model=model,
        )
        self.tracks[track_id] = record
        self.executor.submit(self._separate_track, track_id)
        return record

    def get_track(self, track_id: str) -> TrackRecord | None:
        return self.tracks.get(track_id)

    def render_track(self, track_id: str, params: RenderParams) -> TrackRecord:
        record = self.require_track(track_id)
        self._set_status(record, "rendering")
        self.executor.submit(self._render_track, track_id, params)
        return record

    def require_track(self, track_id: str) -> TrackRecord:
        record = self.get_track(track_id)
        if record is None:
            raise KeyError(track_id)
        return record

    def to_payload(self, record: TrackRecord) -> dict:
        payload = asdict(record)
        payload["urls"] = {
            "original": f"/api/v1/tracks/{record.track_id}/audio/original",
            "stems": {
                stem: f"/api/v1/tracks/{record.track_id}/stems/{stem}"
                for stem in STEM_NAMES
                if record.stems_dir and (Path(record.stems_dir) / f"{stem}.wav").exists()
            },
            "download": f"/api/v1/tracks/{record.track_id}/download"
            if record.output_path
            else None,
        }
        return payload

    def _separate_track(self, track_id: str) -> None:
        record = self.tracks[track_id]
        try:
            self._set_status(record, "separating")
            stems_dir = _run_demucs(Path(record.original_path), Path(record.work_dir), record.model)
            record.stems_dir = str(stems_dir)
            self._set_status(record, "ready_to_mix")
        except Exception as exc:
            self._set_status(record, "failed", str(exc))

    def _render_track(self, track_id: str, params: RenderParams) -> None:
        record = self.tracks[track_id]
        try:
            if not record.stems_dir:
                raise ValueError("Track is not separated yet")

            output_path = Path(record.work_dir) / "master.wav"
            report_path = Path(record.work_dir) / "master.report.json"
            result = process_rebalance_master(
                record.original_path,
                output_path,
                model=record.model,
                stems_dir=record.stems_dir,
                profile_name=params.profile,
                mastering_preset=params.mastering_preset,
                report_path=report_path,
                skip_final_master=params.skip_final_master,
                control_overrides=params.controls,
            )
            record.output_path = result["output"]
            record.report_path = result["report"]
            self._set_status(record, "done")
        except Exception as exc:
            self._set_status(record, "failed", str(exc))

    def _set_status(
        self,
        record: TrackRecord,
        status: TrackStatus,
        error_message: str | None = None,
    ) -> None:
        record.status = status
        record.error_message = error_message
        record.updated_at = datetime.now(timezone.utc).isoformat()

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO

from mastering.config import SETTINGS
from mastering.jobs.models import JobEvent, JobStage, RenderParams, TrackRecord, TrackStatus
from mastering.jobs.repository import FileTrackRepository
from mastering.jobs.runner import JobQueueFullError, LocalJobRunner
from mastering.stems.rebalance_master import process_rebalance_master
from mastering.stems.stem_lab import _run_demucs
from mastering.storage.track_storage import TrackStorage

ACTIVE_STATUSES: tuple[TrackStatus, ...] = ("uploaded", "separating", "rendering")


class TrackJobService:
    def __init__(
        self,
        root_dir: Path,
        max_workers: int = SETTINGS.max_workers,
        max_queued_jobs: int = SETTINGS.max_queued_jobs,
    ) -> None:
        self.root_dir = root_dir.resolve()
        self.repository = FileTrackRepository(self.root_dir)
        self.storage = TrackStorage(self.root_dir)
        self.runner = LocalJobRunner(max_workers=max_workers, max_queued_jobs=max_queued_jobs)
        self.tracks = self._load_tracks()
        self.cleanup_expired_tracks()

    def create_track(
        self,
        file_obj: BinaryIO,
        filename: str | None,
        model: str = "mdx_extra",
    ) -> TrackRecord:
        self._validate_model(model)
        reservation = self.runner.reserve()
        track_id = uuid.uuid4().hex
        try:
            upload = self.storage.save_upload(track_id, file_obj, filename)

            record = TrackRecord(
                track_id=track_id,
                status="uploaded",
                original_path=str(upload.original_path),
                work_dir=str(upload.work_dir),
                model=model,
            )
            self._set_progress(
                record,
                "upload_saved",
                "Upload saved. Separation is queued.",
                progress=15,
                persist=False,
            )
            self.tracks[track_id] = record
            self.repository.save(record)
            self._set_progress(
                record,
                "queued_separation",
                "Waiting for the separation worker.",
                progress=20,
            )
            reservation.submit(self._separate_track, track_id)
            return record
        except Exception:
            reservation.release()
            raise

    def get_track(self, track_id: str) -> TrackRecord | None:
        return self.tracks.get(track_id)

    def render_track(self, track_id: str, params: RenderParams) -> TrackRecord:
        record = self.require_track(track_id)
        reservation = self.runner.reserve()
        try:
            self._set_status(
                record,
                "rendering",
                stage="queued_render",
                progress=72,
                progress_detail="Render queued with the current controls.",
            )
            reservation.submit(self._render_track, track_id, params)
            return record
        except Exception:
            reservation.release()
            raise

    def require_track(self, track_id: str) -> TrackRecord:
        record = self.get_track(track_id)
        if record is None:
            raise KeyError(track_id)
        return record

    def delete_track(self, track_id: str) -> None:
        record = self.require_track(track_id)
        if record.status in ACTIVE_STATUSES:
            raise ValueError(f"Track is {record.status} and cannot be deleted yet")

        self.tracks.pop(track_id, None)
        self.repository.delete(track_id)
        self.storage.delete_track_dir(track_id)

    def cleanup_expired_tracks(self, now: datetime | None = None) -> list[str]:
        now = now or datetime.now(timezone.utc)
        deleted: list[str] = []

        for track_id, record in list(self.tracks.items()):
            if record.status in ACTIVE_STATUSES:
                continue
            if not self._is_expired(record, now):
                continue

            self.tracks.pop(track_id, None)
            self.repository.delete(track_id)
            self.storage.delete_track_dir(track_id)
            deleted.append(track_id)

        return deleted

    def health(self) -> dict:
        return {
            "tracks": len(self.tracks),
            "active_tracks": sum(1 for record in self.tracks.values() if record.status in ACTIVE_STATUSES),
            "queue": {
                "capacity": self.runner.capacity,
                "in_flight": self.runner.in_flight,
                "available_slots": self.runner.available_slots,
            },
        }

    def ensure_ready(self) -> None:
        if self.runner.available_slots <= 0:
            raise JobQueueFullError("Processing queue is full. Please try again later.")

    def _separate_track(self, track_id: str) -> None:
        record = self.tracks[track_id]
        try:
            self._set_status(
                record,
                "separating",
                stage="separating",
                progress=35,
                progress_detail="Separating vocals, drums, bass and music.",
            )
            stems_dir = _run_demucs(Path(record.original_path), Path(record.work_dir), record.model)
            self._set_progress(
                record,
                "writing_stems",
                "Separated stems are being written to disk.",
                progress=62,
            )
            record.stems_dir = str(stems_dir)
            self._set_status(
                record,
                "ready_to_mix",
                stage="preview_ready",
                progress=70,
                progress_detail="Stems are ready for browser preview.",
            )
        except Exception as exc:
            self._set_status(
                record,
                "failed",
                str(exc),
                stage="failed",
                progress=100,
                progress_detail=str(exc),
            )

    def _render_track(self, track_id: str, params: RenderParams) -> None:
        record = self.tracks[track_id]
        try:
            if not record.stems_dir:
                raise ValueError("Track is not separated yet")

            self._set_progress(
                record,
                "rendering_master",
                "Rendering the final master with current controls.",
                progress=82,
            )
            output_path = self.storage.master_path(track_id)
            report_path = self.storage.report_path(track_id)
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
                mix_mode=params.mix_mode,
            )
            record.output_path = result["output"]
            record.report_path = result["report"]
            self._set_status(
                record,
                "done",
                stage="master_ready",
                progress=100,
                progress_detail="Master is ready to download.",
            )
        except Exception as exc:
            self._set_status(
                record,
                "failed",
                str(exc),
                stage="failed",
                progress=100,
                progress_detail=str(exc),
            )

    def _set_status(
        self,
        record: TrackRecord,
        status: TrackStatus,
        error_message: str | None = None,
        *,
        stage: JobStage | None = None,
        progress: int | None = None,
        progress_detail: str | None = None,
    ) -> None:
        record.status = status
        record.error_message = error_message
        if stage:
            self._apply_progress(record, stage, progress_detail or status, progress)
        record.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(record)

    def _set_progress(
        self,
        record: TrackRecord,
        stage: JobStage,
        message: str,
        progress: int | None = None,
        *,
        persist: bool = True,
    ) -> None:
        self._apply_progress(record, stage, message, progress)
        record.updated_at = datetime.now(timezone.utc).isoformat()
        if persist:
            self.repository.save(record)

    def _apply_progress(
        self,
        record: TrackRecord,
        stage: JobStage,
        message: str,
        progress: int | None,
    ) -> None:
        record.stage = stage
        record.progress = progress
        record.progress_detail = message
        record.events.append(JobEvent(stage=stage, message=message, progress=progress))

    def _load_tracks(self) -> dict[str, TrackRecord]:
        tracks = self.repository.load_all()
        for record in tracks.values():
            if record.status in ACTIVE_STATUSES:
                record.status = "failed"
                record.error_message = "Server restarted while this track was processing. Please upload it again."
                self._apply_progress(record, "failed", record.error_message, 100)
                record.updated_at = datetime.now(timezone.utc).isoformat()
                self.repository.save(record)
        return tracks

    def _validate_model(self, model: str) -> None:
        if model not in SETTINGS.allowed_demucs_models:
            allowed = ", ".join(SETTINGS.allowed_demucs_models)
            raise ValueError(f"Unsupported separation model: {model}. Allowed models: {allowed}")

    def _is_expired(self, record: TrackRecord, now: datetime) -> bool:
        updated_at = self._parse_datetime(record.updated_at)
        retention_hours = (
            SETTINGS.failed_track_retention_hours
            if record.status == "failed"
            else SETTINGS.track_retention_hours
        )
        expires_at = updated_at + timedelta(hours=retention_hours)
        return expires_at <= now

    def _parse_datetime(self, value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

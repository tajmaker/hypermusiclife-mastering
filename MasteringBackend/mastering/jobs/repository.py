import json
from dataclasses import asdict, fields
from pathlib import Path

from mastering.jobs.models import JobEvent, TrackRecord

MANIFEST_NAME = "manifest.json"


class FileTrackRepository:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> dict[str, TrackRecord]:
        records: dict[str, TrackRecord] = {}
        for manifest_path in self.root_dir.glob(f"*/{MANIFEST_NAME}"):
            try:
                record = self._read_manifest(manifest_path)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            records[record.track_id] = record
        return records

    def save(self, record: TrackRecord) -> None:
        manifest_path = self._manifest_path(record.track_id)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(asdict(record), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(manifest_path)

    def delete(self, track_id: str) -> bool:
        manifest_path = self._manifest_path(track_id)
        if not manifest_path.exists():
            return False
        manifest_path.unlink()
        return True

    def _read_manifest(self, manifest_path: Path) -> TrackRecord:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        allowed = {field.name for field in fields(TrackRecord)}
        record_payload = {key: value for key, value in payload.items() if key in allowed}
        record_payload["events"] = [
            event if isinstance(event, JobEvent) else JobEvent(**event)
            for event in record_payload.get("events", [])
        ]
        return TrackRecord(**record_payload)

    def _manifest_path(self, track_id: str) -> Path:
        return self.root_dir / track_id / MANIFEST_NAME

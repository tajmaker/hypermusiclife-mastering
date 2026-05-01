from dataclasses import asdict

from mastering.jobs.models import STEM_NAMES, TrackRecord
from mastering.storage.track_storage import TrackStorage


def track_to_payload(record: TrackRecord, storage: TrackStorage) -> dict:
    payload = asdict(record)
    payload["urls"] = {
        "original": f"/api/v1/tracks/{record.track_id}/audio/original",
        "stems": {
            stem: f"/api/v1/tracks/{record.track_id}/stems/{stem}"
            for stem in STEM_NAMES
            if record.stems_dir and storage.stem_path(record.stems_dir, stem).exists()
        },
        "download": f"/api/v1/tracks/{record.track_id}/download" if record.output_path else None,
    }
    return payload

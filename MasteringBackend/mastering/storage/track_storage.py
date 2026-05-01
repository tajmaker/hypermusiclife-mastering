from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import BinaryIO

from mastering.config import SETTINGS
from mastering.jobs.models import StemName

UPLOAD_CHUNK_SIZE = 1024 * 1024


class UploadRejectedError(ValueError):
    status_code = 400


class EmptyUploadError(UploadRejectedError):
    pass


class UploadTooLargeError(UploadRejectedError):
    status_code = 413


class UnsupportedUploadTypeError(UploadRejectedError):
    pass


class UnsafeTrackPathError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredUpload:
    original_path: Path
    suffix: str
    work_dir: Path


class TrackStorage:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def work_dir(self, track_id: str) -> Path:
        return self.root_dir / track_id

    def delete_track_dir(self, track_id: str) -> bool:
        work_dir = self._safe_work_dir(track_id)
        if not work_dir.exists():
            return False
        shutil.rmtree(work_dir)
        return True

    def save_upload(
        self,
        track_id: str,
        file_obj: BinaryIO,
        filename: str | None,
    ) -> StoredUpload:
        suffix = self._safe_suffix(filename)
        work_dir = self.work_dir(track_id)
        work_dir.mkdir(parents=True, exist_ok=True)

        original_path = work_dir / f"original{suffix}"
        max_bytes = SETTINGS.max_upload_size_mb * 1024 * 1024
        written = 0
        with original_path.open("wb") as handle:
            while True:
                chunk = file_obj.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    handle.close()
                    original_path.unlink(missing_ok=True)
                    raise UploadTooLargeError(f"File is too large. Limit is {SETTINGS.max_upload_size_mb} MB")
                handle.write(chunk)

        if written == 0:
            original_path.unlink(missing_ok=True)
            raise EmptyUploadError("Uploaded file is empty")

        return StoredUpload(
            original_path=original_path,
            suffix=suffix,
            work_dir=work_dir,
        )

    def stem_path(self, stems_dir: str | Path, stem_name: StemName | str) -> Path:
        return Path(stems_dir) / f"{stem_name}.wav"

    def master_path(self, track_id: str) -> Path:
        return self.work_dir(track_id) / "master.wav"

    def report_path(self, track_id: str) -> Path:
        return self.work_dir(track_id) / "master.report.json"

    def _safe_work_dir(self, track_id: str) -> Path:
        work_dir = self.work_dir(track_id).resolve()
        if work_dir == self.root_dir or self.root_dir not in work_dir.parents:
            raise UnsafeTrackPathError(f"Unsafe track work dir: {work_dir}")
        return work_dir

    def _safe_suffix(self, filename: str | None) -> str:
        suffix = Path(filename or "input.wav").suffix.lower() or ".wav"
        if suffix not in SETTINGS.allowed_upload_extensions:
            allowed = ", ".join(SETTINGS.allowed_upload_extensions)
            raise UnsupportedUploadTypeError(f"Unsupported file type. Allowed extensions: {allowed}")
        return suffix

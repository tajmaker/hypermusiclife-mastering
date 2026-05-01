import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    values = tuple(value.strip() for value in raw.split(",") if value.strip())
    return values or default


@dataclass(frozen=True)
class Settings:
    min_sample_rate_hz: int = 44100
    output_subtype: str = "PCM_24"
    true_peak_oversample_factor: int = 4
    max_retries: int = 1
    min_gain_db: float = -6.0
    safety_true_peak_warn_dbtp: float = -0.8
    safety_min_crest_db: float = 5.0
    safety_max_crest_drop_db: float = 4.0
    safety_max_limiter_avg_gr_db: float = 5.0
    max_upload_size_mb: int = 80
    allowed_upload_extensions: tuple[str, ...] = (
        ".wav",
        ".mp3",
        ".aiff",
        ".aif",
        ".flac",
        ".ogg",
        ".oga",
    )
    allowed_demucs_models: tuple[str, ...] = (
        "mdx_extra",
        "htdemucs",
        "htdemucs_ft",
        "htdemucs_6s",
    )
    track_retention_hours: int = 24
    failed_track_retention_hours: int = 6
    max_workers: int = 1
    max_queued_jobs: int = 2


SETTINGS = Settings(
    max_upload_size_mb=_env_int("MASTERING_MAX_UPLOAD_SIZE_MB", Settings.max_upload_size_mb),
    allowed_upload_extensions=_env_tuple(
        "MASTERING_ALLOWED_UPLOAD_EXTENSIONS",
        Settings.allowed_upload_extensions,
    ),
    allowed_demucs_models=_env_tuple("MASTERING_ALLOWED_DEMUCS_MODELS", Settings.allowed_demucs_models),
    track_retention_hours=_env_int("MASTERING_TRACK_RETENTION_HOURS", Settings.track_retention_hours),
    failed_track_retention_hours=_env_int(
        "MASTERING_FAILED_TRACK_RETENTION_HOURS",
        Settings.failed_track_retention_hours,
    ),
    max_workers=_env_int("MASTERING_MAX_WORKERS", Settings.max_workers),
    max_queued_jobs=_env_int("MASTERING_MAX_QUEUED_JOBS", Settings.max_queued_jobs),
)


from dataclasses import dataclass


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


SETTINGS = Settings()


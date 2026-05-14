from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

TrackStatus = Literal["uploaded", "separating", "ready_to_mix", "rendering", "done", "failed"]
StemName = Literal["vocals", "drums", "bass", "other"]
JobStage = Literal[
    "upload_saved",
    "queued_separation",
    "separating",
    "writing_stems",
    "preview_ready",
    "queued_render",
    "rendering_master",
    "master_ready",
    "failed",
]

STEM_NAMES: tuple[StemName, ...] = ("vocals", "drums", "bass", "other")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobEvent:
    stage: JobStage
    message: str
    progress: int | None = None
    created_at: str = field(default_factory=utc_now_iso)


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
    stage: JobStage | None = None
    progress: int | None = None
    progress_detail: str | None = None
    original_lufs: float | None = None
    rendered_lufs: float | None = None
    lufs_delta: float | None = None
    events: list[JobEvent] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class RenderParams:
    profile: str
    mastering_preset: str
    controls: dict[str, float]
    mix_project: dict[str, Any] | None = None
    mix_mode: str = "delta"
    skip_final_master: bool = False

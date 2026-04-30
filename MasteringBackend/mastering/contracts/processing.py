from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingStats:
    gain_db: float
    limiter_avg_gr_db: float
    safety_flags: tuple[str, ...]


@dataclass(frozen=True)
class ProcessorResult:
    stats: ProcessingStats


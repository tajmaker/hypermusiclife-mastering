from dataclasses import dataclass
from typing import Literal


PresetName = Literal["standard", "gentle", "balanced"]


@dataclass(frozen=True)
class SpectralAdjustments:
    low_shelf_db: float
    high_shelf_db: float


@dataclass
class Strategy:
    target_lufs: float
    target_true_peak: float
    input_trim_db: float
    hpf_cutoff_hz: float
    apply_compression: bool
    compressor_threshold_db: float
    compressor_ratio: float
    compressor_attack_ms: float
    compressor_release_ms: float
    limiter_release_ms: float
    spectral_adjustments: SpectralAdjustments
    max_gain_increase_db: float


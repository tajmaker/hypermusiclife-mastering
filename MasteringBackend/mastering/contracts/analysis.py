from dataclasses import dataclass
from typing import Literal


LoudnessClass = Literal["very_quiet", "moderate", "already_loud"]
DynamicsClass = Literal["high_crest", "mid_crest", "low_crest"]
SpectrumClass = Literal["bass_heavy", "balanced", "bright", "dark"]


@dataclass(frozen=True)
class BandEnergies:
    low_db: float
    mid_db: float
    high_db: float
    low_vs_mid_db: float
    high_vs_mid_db: float


@dataclass(frozen=True)
class AnalysisResult:
    lufs: float
    true_peak: float
    rms: float
    crest: float
    lra: float
    band_energies: BandEnergies
    spectrum_class: SpectrumClass
    loudness_class: LoudnessClass
    dynamics_class: DynamicsClass
    stereo_corr: float
    mid_side_ratio_db: float


import numpy as np

from mastering.contracts.analysis import AnalysisResult
from mastering.contracts.decision import PresetName, Strategy
from mastering.contracts.processing import ProcessingStats
from mastering.domain.analyzer import analyze_track
from mastering.domain.decision_engine import decide_strategy
from mastering.domain.processor import safety_and_reprocess_if_needed


def analyze_single(audio: np.ndarray, sample_rate: int) -> AnalysisResult:
    return analyze_track(audio, sample_rate)


def run_mastering_pipeline(
    audio: np.ndarray,
    sample_rate: int,
    preset: PresetName = "standard",
) -> tuple[np.ndarray, AnalysisResult, Strategy, AnalysisResult, ProcessingStats]:
    before = analyze_track(audio, sample_rate)
    strategy = decide_strategy(before, preset=preset)
    processed, after, stats = safety_and_reprocess_if_needed(audio, sample_rate, strategy)
    return processed, before, strategy, after, stats


from typing import Tuple

import numpy as np
import pyloudnorm as pyln
from pedalboard import (
    Compressor,
    HighpassFilter,
    HighShelfFilter,
    Limiter,
    LowShelfFilter,
    Pedalboard,
)

from mastering.config import SETTINGS
from mastering.contracts.analysis import AnalysisResult
from mastering.contracts.decision import Strategy
from mastering.contracts.processing import ProcessingStats
from mastering.domain.analyzer import analyze_track
from mastering.utils.audio_math import apply_gain_linear, db_to_lin, ensure_2d, to_mono


def build_board(strategy: Strategy) -> Pedalboard:
    fx = [HighpassFilter(cutoff_frequency_hz=strategy.hpf_cutoff_hz)]
    if strategy.apply_compression and strategy.compressor_ratio > 1.0:
        fx.append(
            Compressor(
                threshold_db=strategy.compressor_threshold_db,
                ratio=strategy.compressor_ratio,
                attack_ms=strategy.compressor_attack_ms,
                release_ms=strategy.compressor_release_ms,
            )
        )
    low_shelf_db = float(np.clip(strategy.spectral_adjustments.low_shelf_db, -1.5, 1.5))
    high_shelf_db = float(np.clip(strategy.spectral_adjustments.high_shelf_db, -1.5, 1.5))
    if abs(low_shelf_db) >= 0.1:
        fx.append(LowShelfFilter(cutoff_frequency_hz=100.0, gain_db=low_shelf_db))
    if abs(high_shelf_db) >= 0.1:
        fx.append(HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=high_shelf_db))
    fx.append(Limiter(threshold_db=strategy.target_true_peak, release_ms=strategy.limiter_release_ms))
    return Pedalboard(fx)


def loudness_gain_to_target(audio: np.ndarray, sample_rate: int, strategy: Strategy) -> float:
    meter = pyln.Meter(sample_rate)
    current_lufs = float(meter.integrated_loudness(to_mono(audio)))
    raw_needed = strategy.target_lufs - current_lufs
    return float(np.clip(raw_needed, SETTINGS.min_gain_db, strategy.max_gain_increase_db))


def estimate_limiter_gr_db(before: np.ndarray, after: np.ndarray, threshold_db: float) -> float:
    thr = db_to_lin(threshold_db)
    mag_in = np.max(np.abs(np.asarray(before, dtype=np.float64)), axis=1)
    mag_out = np.max(np.abs(np.asarray(after, dtype=np.float64)), axis=1)
    mask = mag_in > thr
    if not np.any(mask):
        return 0.0
    ratio = mag_out[mask] / (mag_in[mask] + 1e-12)
    return float(np.mean(-20.0 * np.log10(np.clip(ratio, 1e-6, 1.0))))


def process_once(audio: np.ndarray, sample_rate: int, strategy: Strategy) -> Tuple[np.ndarray, ProcessingStats]:
    board = build_board(strategy)
    y = ensure_2d(audio)
    if abs(strategy.input_trim_db) > 1e-6:
        y = apply_gain_linear(y, strategy.input_trim_db)
    y = board(y, sample_rate)
    gain_db = loudness_gain_to_target(y, sample_rate, strategy)
    y = apply_gain_linear(y, gain_db)
    limiter = Limiter(threshold_db=strategy.target_true_peak, release_ms=strategy.limiter_release_ms)
    before_lim = y.copy()
    y = limiter(y, sample_rate)
    return y, ProcessingStats(
        gain_db=gain_db,
        limiter_avg_gr_db=estimate_limiter_gr_db(before_lim, y, strategy.target_true_peak),
        safety_flags=tuple(),
    )


def safety_and_reprocess_if_needed(
    original_audio: np.ndarray,
    sample_rate: int,
    strategy: Strategy,
) -> Tuple[np.ndarray, AnalysisResult, ProcessingStats]:
    attempt = 0
    last_analysis = analyze_track(original_audio, sample_rate)
    last_stats = ProcessingStats(gain_db=0.0, limiter_avg_gr_db=0.0, safety_flags=tuple())
    last_out = ensure_2d(original_audio)
    all_flags: set[str] = set()

    while attempt <= SETTINGS.max_retries:
        out, stats = process_once(original_audio, sample_rate, strategy)
        out_analysis = analyze_track(out, sample_rate)
        flags = []
        if out_analysis.true_peak > SETTINGS.safety_true_peak_warn_dbtp:
            flags.append("true_peak_risk")
        if out_analysis.crest < SETTINGS.safety_min_crest_db:
            flags.append("over_compressed")
        if (last_analysis.crest - out_analysis.crest) > SETTINGS.safety_max_crest_drop_db:
            flags.append("too_much_dynamics_loss")
        if stats.limiter_avg_gr_db > SETTINGS.safety_max_limiter_avg_gr_db:
            flags.append("limiter_working_too_hard")
        if last_analysis.lra > 8.0 and out_analysis.lra < max(4.0, last_analysis.lra - 4.0):
            flags.append("too_much_lra_loss")
        all_flags.update(flags)

        if flags and attempt < SETTINGS.max_retries:
            strategy.target_lufs -= 2.0
            attempt += 1
            continue

        if out_analysis.true_peak > strategy.target_true_peak:
            diff = out_analysis.true_peak - strategy.target_true_peak
            out = apply_gain_linear(out, -diff)
            out_analysis = analyze_track(out, sample_rate)

        last_out = np.clip(out, -1.0, 1.0).astype(np.float32, copy=False)
        last_analysis = out_analysis
        last_stats = ProcessingStats(
            gain_db=stats.gain_db,
            limiter_avg_gr_db=stats.limiter_avg_gr_db,
            safety_flags=tuple(sorted(all_flags)),
        )
        break

    return last_out, last_analysis, last_stats


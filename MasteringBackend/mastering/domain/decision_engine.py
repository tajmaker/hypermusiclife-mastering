from mastering.contracts.analysis import AnalysisResult
from mastering.contracts.decision import PresetName, SpectralAdjustments, Strategy


def decide_strategy(analysis: AnalysisResult, preset: PresetName = "standard") -> Strategy:
    # North star: first 30 seconds of a mastering engineer.
    # 1) Is source already hot/clipped? 2) Is it over-dense? 3) Is tonal balance skewed?
    # The rest of decisions should only make minimal changes to address these findings.

    target_true_peak = -1.0
    hpf_cutoff_hz = 25.0
    limiter_release_ms = 150.0
    compressor_attack_ms = 30.0
    compressor_release_ms = 200.0
    compressor_threshold_db = -18.0
    input_trim_db = 0.0

    if analysis.loudness_class == "already_loud" and analysis.dynamics_class == "low_crest":
        target_lufs = analysis.lufs
        apply_compression = False
        max_gain_increase_db = 0.0
    elif analysis.loudness_class == "very_quiet":
        target_lufs = -14.0 if preset in ("standard", "balanced") else -16.0
        apply_compression = analysis.dynamics_class != "high_crest"
        max_gain_increase_db = 8.0
    else:
        # Moderate/already-loud material should preserve existing macro-dynamics.
        # The previous targets were too aggressive and forced limiter/backoff behavior.
        if analysis.dynamics_class == "high_crest":
            # Let dynamic material breathe: smaller loudness lift and no compression.
            if preset == "gentle":
                target_lufs = max(-16.5, analysis.lufs + 1.2)
            else:
                target_lufs = max(-16.0, analysis.lufs + 1.6)
            apply_compression = False
            max_gain_increase_db = 2.5
        elif analysis.dynamics_class == "mid_crest":
            target_lufs = -15.0 if preset in ("standard", "balanced") else -15.5
            apply_compression = analysis.loudness_class == "moderate"
            max_gain_increase_db = 3.5
        else:
            # low_crest but not already_loud/low_crest branch
            target_lufs = -14.8 if preset in ("standard", "balanced") else -15.3
            apply_compression = False
            max_gain_increase_db = 2.0

    # Create headroom early on hot material before dynamic processors.
    if analysis.true_peak > -1.0:
        # Pull down to around -3 dBTP equivalent before the chain.
        input_trim_db = -2.0
    elif analysis.true_peak > -2.0:
        input_trim_db = -1.0

    base_ratio = 1.35 if preset in ("standard", "balanced") else 1.25
    compressor_ratio = 1.0 if not apply_compression else base_ratio

    # Dynamic sources get less compression. Dense/loud sources get bypassed.
    if apply_compression:
        if analysis.dynamics_class == "high_crest":
            compressor_threshold_db = -15.0
            compressor_ratio = min(compressor_ratio, 1.25)
        elif analysis.dynamics_class == "mid_crest":
            compressor_threshold_db = -16.5
        else:
            compressor_threshold_db = -13.5
            compressor_ratio = 1.2

    # High stereo decorrelation can become unstable with heavy dynamics.
    if analysis.stereo_corr < 0.75:
        limiter_release_ms = 180.0

    low_adj = 0.0
    high_adj = 0.0
    if analysis.spectrum_class == "bass_heavy":
        if analysis.loudness_class == "very_quiet":
            low_adj = -0.3 if preset == "gentle" else -0.5
        else:
            low_adj = 0.5 if preset == "gentle" else 1.0
    if analysis.spectrum_class == "bright":
        high_adj = -0.5 if preset == "gentle" else -1.0
    if analysis.spectrum_class == "dark":
        high_adj = 0.5 if preset == "gentle" else 1.0

    return Strategy(
        target_lufs=target_lufs,
        target_true_peak=target_true_peak,
        input_trim_db=input_trim_db,
        hpf_cutoff_hz=hpf_cutoff_hz,
        apply_compression=apply_compression,
        compressor_threshold_db=compressor_threshold_db,
        compressor_ratio=compressor_ratio,
        compressor_attack_ms=compressor_attack_ms,
        compressor_release_ms=compressor_release_ms,
        limiter_release_ms=limiter_release_ms,
        spectral_adjustments=SpectralAdjustments(
            low_shelf_db=low_adj,
            high_shelf_db=high_adj,
        ),
        max_gain_increase_db=max_gain_increase_db,
    )


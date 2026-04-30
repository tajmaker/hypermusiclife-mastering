from mastering.contracts.analysis import AnalysisResult
from mastering.contracts.decision import Strategy


def print_analysis(label: str, a: AnalysisResult) -> None:
    print(f"\n=== {label} ANALYSIS ===")
    print(f"LUFS:        {a.lufs:.2f} LUFS")
    print(f"True Peak:   {a.true_peak:.2f} dBTP")
    print(f"RMS:         {a.rms:.2f} dBFS")
    print(f"Crest:       {a.crest:.2f} dB")
    print(f"LRA:         {a.lra:.2f} LU")
    be = a.band_energies
    print(
        f"Spectrum (dB): low {be.low_db:.2f}, mid {be.mid_db:.2f}, high {be.high_db:.2f}, "
        f"low-mid {be.low_vs_mid_db:.2f}, high-mid {be.high_vs_mid_db:.2f}"
    )
    print(f"Stereo:     corr {a.stereo_corr:.2f}, mid/side {a.mid_side_ratio_db:.2f} dB")
    print(
        f"Classes: loudness={a.loudness_class}, dynamics={a.dynamics_class}, spectrum={a.spectrum_class}"
    )


def print_before_after(before: AnalysisResult, after: AnalysisResult) -> None:
    print("\n=== BEFORE / AFTER COMPARISON ===")
    print(f"LUFS:      {before.lufs:.2f} -> {after.lufs:.2f}")
    print(f"TruePeak:  {before.true_peak:.2f} -> {after.true_peak:.2f}")
    print(f"Crest:     {before.crest:.2f} -> {after.crest:.2f}")
    print(f"LRA:       {before.lra:.2f} -> {after.lra:.2f}")


def print_pair_comparison(ref: AnalysisResult, test: AnalysisResult, ref_label: str, test_label: str) -> None:
    print("\n=== PAIR COMPARISON ===")
    print(f"Reference: {ref_label}")
    print(f"Test:      {test_label}\n")
    print(f"{'Metric':12s} {'Ref':>10s} {'Test':>10s} {'Delta':>12s}")
    print("-" * 48)
    print(f"{'LUFS':12s} {ref.lufs:10.2f} {test.lufs:10.2f} {(test.lufs - ref.lufs):12.2f}")
    print(f"{'TruePeak':12s} {ref.true_peak:10.2f} {test.true_peak:10.2f} {(test.true_peak - ref.true_peak):12.2f}")
    print(f"{'RMS':12s} {ref.rms:10.2f} {test.rms:10.2f} {(test.rms - ref.rms):12.2f}")
    print(f"{'Crest':12s} {ref.crest:10.2f} {test.crest:10.2f} {(test.crest - ref.crest):12.2f}")
    print(f"{'LRA':12s} {ref.lra:10.2f} {test.lra:10.2f} {(test.lra - ref.lra):12.2f}")
    print(
        f"{'Low dB':12s} {ref.band_energies.low_db:10.2f} {test.band_energies.low_db:10.2f} "
        f"{(test.band_energies.low_db - ref.band_energies.low_db):12.2f}"
    )
    print(
        f"{'Mid dB':12s} {ref.band_energies.mid_db:10.2f} {test.band_energies.mid_db:10.2f} "
        f"{(test.band_energies.mid_db - ref.band_energies.mid_db):12.2f}"
    )
    print(
        f"{'High dB':12s} {ref.band_energies.high_db:10.2f} {test.band_energies.high_db:10.2f} "
        f"{(test.band_energies.high_db - ref.band_energies.high_db):12.2f}"
    )
    print(
        f"{'StereoCorr':12s} {ref.stereo_corr:10.2f} {test.stereo_corr:10.2f} "
        f"{(test.stereo_corr - ref.stereo_corr):12.2f}"
    )
    print(
        f"{'Mid/Side dB':12s} {ref.mid_side_ratio_db:10.2f} {test.mid_side_ratio_db:10.2f} "
        f"{(test.mid_side_ratio_db - ref.mid_side_ratio_db):12.2f}"
    )


def print_strategy(strategy: Strategy, preset: str) -> None:
    print("\n=== STRATEGY DECISION ===")
    print(f"Preset:          {preset}")
    print(f"Target LUFS:     {strategy.target_lufs:.2f}")
    print(f"Target TruePeak: {strategy.target_true_peak:.2f} dBTP")
    print(f"Input trim:      {strategy.input_trim_db:+.2f} dB")
    print(f"HPF cutoff:      {strategy.hpf_cutoff_hz:.1f} Hz")
    print(f"Apply comp:      {strategy.apply_compression} (ratio {strategy.compressor_ratio:.2f})")
    print(
        f"Comp params:     th {strategy.compressor_threshold_db:.1f} dB, "
        f"atk {strategy.compressor_attack_ms:.1f} ms, rel {strategy.compressor_release_ms:.1f} ms"
    )
    print(
        f"Spectral adj:    low {strategy.spectral_adjustments.low_shelf_db:+.2f} dB @100Hz, "
        f"high {strategy.spectral_adjustments.high_shelf_db:+.2f} dB @8kHz"
    )
    print(f"Limiter rel:     {strategy.limiter_release_ms:.1f} ms")
    print(f"Max gain +:      {strategy.max_gain_increase_db:.1f} dB")


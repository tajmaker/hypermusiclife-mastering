import argparse
from pathlib import Path
from typing import cast

from mastering.contracts.decision import PresetName
from mastering.orchestration.regression_runner import (
    collect_track_metrics,
    discover_input_tracks,
    evaluate_regression,
    save_baseline_run,
    _load_baseline_map,
)


GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def _c(text: str, severity: str) -> str:
    if severity == "fail":
        return f"{RED}{text}{RESET}"
    if severity == "warn":
        return f"{YELLOW}{text}{RESET}"
    return f"{GREEN}{text}{RESET}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reference-based mastering regression suite.")
    parser.add_argument("--inputs-dir", required=True, help="Folder with input WAV/AIFF tracks.")
    parser.add_argument(
        "--baselines-dir",
        default="regression_baselines",
        help="Folder for baseline runs (timestamped JSON per track).",
    )
    parser.add_argument("--preset", choices=["standard", "gentle", "balanced"], default="balanced")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Save this run as new baseline (explicit action only).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_dir = Path(args.inputs_dir).resolve()
    baselines_dir = Path(args.baselines_dir).resolve()
    tracks = discover_input_tracks(input_dir)
    if not tracks:
        raise SystemExit(f"No WAV/AIFF tracks found in: {input_dir}")

    baseline_ts, baseline_map = _load_baseline_map(baselines_dir)
    if baseline_ts:
        print(f"Baseline: {baseline_ts}")
    else:
        print("Baseline: none")

    results = []
    current_metrics = []
    preset = cast(PresetName, args.preset)
    for track in tracks:
        metric = collect_track_metrics(track, preset=preset)
        current_metrics.append(metric)
        base = baseline_map.get(metric.track_name)
        results.append(evaluate_regression(metric, base))

    print("\n=== REGRESSION REPORT ===")
    overall = "PASS"
    for result in results:
        status = result.status
        if status == "FAIL":
            overall = "FAIL"
        elif status == "WARN" and overall != "FAIL":
            overall = "WARN"
        print(_c(f"\n[{status}] {result.metrics.track_name}", status.lower()))
        print(
            f"  LUFS {result.metrics.lufs_before:.2f} -> {result.metrics.lufs_after:.2f} | "
            f"TP {result.metrics.true_peak_before:.2f} -> {result.metrics.true_peak_after:.2f} | "
            f"Crest {result.metrics.crest_before:.2f} -> {result.metrics.crest_after:.2f} | "
            f"LRA {result.metrics.lra_before:.2f} -> {result.metrics.lra_after:.2f}"
        )
        print(
            f"  Limiter avg GR: {result.metrics.limiter_avg_gr_db:.2f} dB | "
            f"Spectral shifts L/M/H: {result.metrics.spectral_shift_low_db:+.2f} / "
            f"{result.metrics.spectral_shift_mid_db:+.2f} / {result.metrics.spectral_shift_high_db:+.2f} dB"
        )
        for check in result.checks:
            print(f"   - {_c(check.message, check.severity)}")

    print(f"\nOverall: {_c(overall, overall.lower())}")

    if args.update_baseline:
        ts = save_baseline_run(baselines_dir, current_metrics)
        print(f"Baseline updated: {ts}")
    else:
        print("Baseline not updated (use --update-baseline).")

    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())


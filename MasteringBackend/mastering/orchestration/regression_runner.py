import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mastering.contracts.decision import PresetName
from mastering.contracts.regression import TrackRunMetrics
from mastering.orchestration.pipeline import run_mastering_pipeline
from mastering.storage.audio_io import read_audio


@dataclass(frozen=True)
class MetricCheck:
    name: str
    severity: str  # ok | warn | fail
    message: str


@dataclass(frozen=True)
class TrackRegressionResult:
    metrics: TrackRunMetrics
    checks: tuple[MetricCheck, ...]

    @property
    def status(self) -> str:
        severities = {c.severity for c in self.checks}
        if "fail" in severities:
            return "FAIL"
        if "warn" in severities:
            return "WARN"
        return "PASS"


def collect_track_metrics(track_path: Path, preset: PresetName) -> TrackRunMetrics:
    audio, sample_rate = read_audio(str(track_path))
    _processed, before, _strategy, after, stats = run_mastering_pipeline(audio, sample_rate, preset=preset)
    return TrackRunMetrics(
        track_name=track_path.name,
        lufs_before=before.lufs,
        lufs_after=after.lufs,
        true_peak_before=before.true_peak,
        true_peak_after=after.true_peak,
        crest_before=before.crest,
        crest_after=after.crest,
        lra_before=before.lra,
        lra_after=after.lra,
        limiter_avg_gr_db=stats.limiter_avg_gr_db,
        spectral_shift_low_db=after.band_energies.low_db - before.band_energies.low_db,
        spectral_shift_mid_db=after.band_energies.mid_db - before.band_energies.mid_db,
        spectral_shift_high_db=after.band_energies.high_db - before.band_energies.high_db,
        safety_flags=stats.safety_flags,
    )


def _check_delta(name: str, current: float, baseline: float, warn_abs: float, fail_abs: float) -> MetricCheck:
    delta = current - baseline
    abs_delta = abs(delta)
    if abs_delta >= fail_abs:
        return MetricCheck(name=name, severity="fail", message=f"{name} delta {delta:+.2f} (>{fail_abs:.2f})")
    if abs_delta >= warn_abs:
        return MetricCheck(name=name, severity="warn", message=f"{name} delta {delta:+.2f} (>{warn_abs:.2f})")
    return MetricCheck(name=name, severity="ok", message=f"{name} delta {delta:+.2f}")


def evaluate_regression(current: TrackRunMetrics, baseline: TrackRunMetrics | None) -> TrackRegressionResult:
    checks: list[MetricCheck] = []

    # Hard quality guards independent of baseline.
    if current.true_peak_after > -0.8:
        checks.append(MetricCheck("true_peak_after", "fail", f"true peak {current.true_peak_after:+.2f} dBTP > -0.8"))
    if current.crest_after < 5.0:
        checks.append(MetricCheck("crest_after", "fail", f"crest {current.crest_after:.2f} dB < 5.0"))
    if current.limiter_avg_gr_db > 5.0:
        checks.append(MetricCheck("limiter_avg_gr", "fail", f"limiter avg GR {current.limiter_avg_gr_db:.2f} dB > 5.0"))
    if current.safety_flags:
        checks.append(MetricCheck("safety_flags", "warn", f"flags: {', '.join(current.safety_flags)}"))
    else:
        checks.append(MetricCheck("safety_flags", "ok", "flags: none"))

    # Baseline comparisons.
    if baseline is None:
        checks.append(MetricCheck("baseline", "warn", "no baseline available"))
        return TrackRegressionResult(metrics=current, checks=tuple(checks))

    checks.extend(
        [
            _check_delta("lufs_after", current.lufs_after, baseline.lufs_after, warn_abs=0.7, fail_abs=1.5),
            _check_delta("true_peak_after", current.true_peak_after, baseline.true_peak_after, warn_abs=0.3, fail_abs=0.8),
            _check_delta("crest_after", current.crest_after, baseline.crest_after, warn_abs=1.0, fail_abs=2.0),
            _check_delta("lra_after", current.lra_after, baseline.lra_after, warn_abs=0.8, fail_abs=1.5),
            _check_delta(
                "limiter_avg_gr_db",
                current.limiter_avg_gr_db,
                baseline.limiter_avg_gr_db,
                warn_abs=1.0,
                fail_abs=2.0,
            ),
            _check_delta(
                "spectral_shift_low_db",
                current.spectral_shift_low_db,
                baseline.spectral_shift_low_db,
                warn_abs=1.5,
                fail_abs=3.0,
            ),
            _check_delta(
                "spectral_shift_mid_db",
                current.spectral_shift_mid_db,
                baseline.spectral_shift_mid_db,
                warn_abs=1.0,
                fail_abs=2.5,
            ),
            _check_delta(
                "spectral_shift_high_db",
                current.spectral_shift_high_db,
                baseline.spectral_shift_high_db,
                warn_abs=1.2,
                fail_abs=2.5,
            ),
        ]
    )
    return TrackRegressionResult(metrics=current, checks=tuple(checks))


def discover_input_tracks(input_dir: Path) -> list[Path]:
    exts = {".wav", ".aiff", ".aif"}
    tracks = [p for p in sorted(input_dir.iterdir()) if p.is_file() and p.suffix.lower() in exts]
    return tracks


def _load_baseline_map(baseline_dir: Path) -> tuple[str | None, dict[str, TrackRunMetrics]]:
    latest_file = baseline_dir / "latest.json"
    if not latest_file.exists():
        return None, {}
    meta = json.loads(latest_file.read_text(encoding="utf-8"))
    ts = meta.get("timestamp")
    if not ts:
        return None, {}
    run_dir = baseline_dir / ts
    if not run_dir.exists():
        return None, {}
    data: dict[str, TrackRunMetrics] = {}
    for file in run_dir.glob("*.json"):
        payload = json.loads(file.read_text(encoding="utf-8"))
        metric = TrackRunMetrics.from_dict(payload)
        data[metric.track_name] = metric
    return ts, data


def save_baseline_run(baseline_dir: Path, track_metrics: list[TrackRunMetrics]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = baseline_dir / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    for metric in track_metrics:
        out_path = run_dir / f"{Path(metric.track_name).stem}.json"
        out_path.write_text(json.dumps(metric.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8")
    (baseline_dir / "latest.json").write_text(json.dumps({"timestamp": ts}, indent=2), encoding="utf-8")
    return ts


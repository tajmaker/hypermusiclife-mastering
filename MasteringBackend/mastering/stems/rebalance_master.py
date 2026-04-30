import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

import soundfile as sf

from mastering.domain.analyzer import analyze_track
from mastering.orchestration.pipeline import run_mastering_pipeline
from mastering.stems.stem_lab import (
    _delta_rebalance_mix,
    _load_stems,
    _resample_audio,
    _run_demucs,
)
from mastering.storage.audio_io import read_audio, write_audio


@dataclass(frozen=True)
class RebalancePreset:
    name: str
    description: str
    vocal_gain: float
    vocal_deharsh: float
    vocal_width: float
    drums_gain: float
    drums_punch: float
    bass_gain: float
    music_gain: float
    music_bright: float
    analog_color: float


PRESETS: dict[str, RebalancePreset] = {
    "safe": RebalancePreset(
        name="safe",
        description="Conservative delta rebalance for SUNO-style mix repair.",
        vocal_gain=0.9,
        vocal_deharsh=35.0,
        vocal_width=0.0,
        drums_gain=0.0,
        drums_punch=22.0,
        bass_gain=-0.6,
        music_gain=0.0,
        music_bright=0.4,
        analog_color=14.0,
    ),
    "vocal": RebalancePreset(
        name="vocal",
        description="Vocal-forward repair with stronger upper-mid softening.",
        vocal_gain=1.2,
        vocal_deharsh=45.0,
        vocal_width=0.0,
        drums_gain=0.0,
        drums_punch=18.0,
        bass_gain=-0.5,
        music_gain=0.0,
        music_bright=0.2,
        analog_color=10.0,
    ),
}

CONTROL_FIELDS = {
    "vocal_gain",
    "vocal_deharsh",
    "vocal_width",
    "drums_gain",
    "drums_punch",
    "bass_gain",
    "music_gain",
    "music_bright",
    "analog_color",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Production-like stem-aware rebalance + mastering CLI."
    )
    parser.add_argument("input_wav", help="Path to source WAV/AIFF/audio file.")
    parser.add_argument("output_wav", help="Path to mastered output WAV.")
    parser.add_argument("--model", default="mdx_extra", help="Demucs model name.")
    parser.add_argument("--stems-dir", help="Reuse an existing Demucs stems folder.")
    parser.add_argument(
        "--profile",
        choices=sorted(PRESETS),
        default="safe",
        help="Rebalance profile.",
    )
    parser.add_argument("--preset", choices=["standard", "gentle", "balanced"], default="balanced")
    parser.add_argument("--report", help="Optional report JSON path.")
    parser.add_argument(
        "--keep-stems",
        action="store_true",
        help="Keep generated stems next to the output when separation runs.",
    )
    parser.add_argument(
        "--skip-final-master",
        action="store_true",
        help="Export only the delta-rebalanced mix.",
    )
    return parser


def _preset_args(preset: RebalancePreset) -> SimpleNamespace:
    return SimpleNamespace(
        vocal_gain=preset.vocal_gain,
        vocal_deharsh=preset.vocal_deharsh,
        vocal_width=preset.vocal_width,
        drums_gain=preset.drums_gain,
        drums_punch=preset.drums_punch,
        bass_gain=preset.bass_gain,
        other_gain=preset.music_gain,
        other_bright=preset.music_bright,
        analog_color=preset.analog_color,
    )


def _preset_with_overrides(
    preset: RebalancePreset,
    overrides: Mapping[str, float] | None,
) -> RebalancePreset:
    if not overrides:
        return preset

    unknown = sorted(set(overrides) - CONTROL_FIELDS)
    if unknown:
        raise ValueError(f"Unknown rebalance controls: {', '.join(unknown)}")

    payload = asdict(preset)
    for name, value in overrides.items():
        payload[name] = float(value)
    return RebalancePreset(**payload)


def _analysis_dict(path: Path) -> dict:
    audio, sample_rate = read_audio(str(path))
    analysis = analyze_track(audio, sample_rate)
    return {
        "sample_rate": sample_rate,
        "lufs": analysis.lufs,
        "true_peak": analysis.true_peak,
        "rms": analysis.rms,
        "crest": analysis.crest,
        "lra": analysis.lra,
        "spectrum_class": analysis.spectrum_class,
        "loudness_class": analysis.loudness_class,
        "dynamics_class": analysis.dynamics_class,
        "stereo_corr": analysis.stereo_corr,
        "mid_side_ratio_db": analysis.mid_side_ratio_db,
    }


def _write_report(
    report_path: Path,
    input_path: Path,
    output_path: Path,
    stems_dir: Path,
    model: str,
    profile: RebalancePreset,
    mastering_preset: str,
    skipped_final_master: bool,
) -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "output": str(output_path),
        "stems_dir": str(stems_dir),
        "model": model,
        "mix_mode": "delta",
        "profile": asdict(profile),
        "mastering_preset": mastering_preset,
        "skip_final_master": skipped_final_master,
        "before": _analysis_dict(input_path),
        "after": _analysis_dict(output_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8-sig")


def process_rebalance_master(
    input_wav: str | Path,
    output_wav: str | Path,
    *,
    model: str = "mdx_extra",
    stems_dir: str | Path | None = None,
    profile_name: str = "safe",
    mastering_preset: str = "balanced",
    report_path: str | Path | None = None,
    keep_stems: bool = False,
    skip_final_master: bool = False,
    control_overrides: Mapping[str, float] | None = None,
) -> dict:
    input_path = Path(input_wav).resolve()
    output_path = Path(output_wav).resolve()
    if profile_name not in PRESETS:
        raise ValueError(f"Unknown profile: {profile_name}")

    target_sample_rate = sf.info(input_path).samplerate
    profile = _preset_with_overrides(PRESETS[profile_name], control_overrides)

    generated_root: Path | None = None
    if stems_dir:
        resolved_stems_dir = Path(stems_dir).resolve()
    else:
        generated_root = Path.cwd() / "stem_runs" / f"{input_path.stem}_{model}_rebalance_master"
        generated_root.mkdir(parents=True, exist_ok=True)
        resolved_stems_dir = _run_demucs(input_path, generated_root, model)

    stems, stem_sample_rate = _load_stems(resolved_stems_dir)
    candidate, candidate_sample_rate = _delta_rebalance_mix(
        input_path,
        stems,
        stem_sample_rate,
        _preset_args(profile),
    )

    if skip_final_master:
        output = candidate
        output_sample_rate = candidate_sample_rate
    else:
        output, _before, _strategy, _after, _stats = run_mastering_pipeline(
            candidate,
            candidate_sample_rate,
            preset=mastering_preset,
        )
        output_sample_rate = candidate_sample_rate

    output = _resample_audio(output, output_sample_rate, target_sample_rate)
    write_audio(str(output_path), output, target_sample_rate)

    if generated_root is not None and keep_stems:
        keep_path = output_path.with_suffix("")
        keep_path = keep_path.parent / f"{keep_path.name}_stems"
        shutil.copytree(resolved_stems_dir, keep_path, dirs_exist_ok=True)
        resolved_stems_dir = keep_path

    if generated_root is not None and not keep_stems:
        shutil.rmtree(generated_root, ignore_errors=True)

    resolved_report_path = (
        Path(report_path).resolve() if report_path else output_path.with_suffix(".report.json")
    )
    _write_report(
        resolved_report_path,
        input_path,
        output_path,
        resolved_stems_dir,
        model,
        profile,
        mastering_preset,
        skip_final_master,
    )
    return {
        "input": str(input_path),
        "output": str(output_path),
        "report": str(resolved_report_path),
        "stems_dir": str(resolved_stems_dir),
        "model": model,
        "profile": profile.name,
        "controls": asdict(profile),
        "mastering_preset": mastering_preset,
        "skip_final_master": skip_final_master,
    }


def main() -> int:
    args = build_parser().parse_args()
    result = process_rebalance_master(
        args.input_wav,
        args.output_wav,
        model=args.model,
        stems_dir=args.stems_dir,
        profile_name=args.profile,
        mastering_preset=args.preset,
        report_path=args.report,
        keep_stems=args.keep_stems,
        skip_final_master=args.skip_final_master,
    )
    if args.keep_stems:
        print(f"Generated stems kept at: {result['stems_dir']}")
    print(f"Rebalance master written: {result['output']}")
    print(f"Report written: {result['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

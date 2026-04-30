import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import soundfile as sf

from mastering.domain.analyzer import analyze_track
from mastering.orchestration.pipeline import run_mastering_pipeline
from mastering.stems.stem_lab import (
    _delta_rebalance_mix,
    _load_stems,
    _process_stems,
    _resample_audio,
    _run_demucs,
)
from mastering.storage.audio_io import read_audio, write_audio


@dataclass(frozen=True)
class RebalanceCase:
    slug: str
    label: str
    purpose: str
    vocal_gain: float = 0.0
    vocal_deharsh: float = 0.0
    vocal_width: float = 0.0
    drums_gain: float = 0.0
    drums_punch: float = 0.0
    bass_gain: float = 0.0
    other_gain: float = 0.0
    other_bright: float = 0.0
    analog_color: float = 0.0


CASES = (
    RebalanceCase(
        slug="01_vocal_repair",
        label="Вокал немного вперёд и мягче",
        purpose="Проверяем, какой способ меньше портит микс при работе с вокалом.",
        vocal_gain=1.2,
        vocal_deharsh=45.0,
        analog_color=8.0,
    ),
    RebalanceCase(
        slug="02_drums_bass_balance",
        label="Барабаны плотнее, бас чуть тише",
        purpose="Проверяем, какой способ лучше переносит rhythm-section rebalance.",
        drums_punch=30.0,
        bass_gain=-0.8,
        analog_color=8.0,
    ),
    RebalanceCase(
        slug="03_minimal_other_touch",
        label="Минимальное касание music/background",
        purpose="Проверяем безопасный минимум для самого проблемного остаточного stem-а.",
        other_bright=0.5,
        analog_color=8.0,
    ),
    RebalanceCase(
        slug="04_balanced_delta_candidate",
        label="Кандидат сбалансированной правки",
        purpose="Проверяем прошлый хороший рецепт через full и delta сборку.",
        vocal_gain=1.1,
        vocal_deharsh=45.0,
        drums_punch=28.0,
        bass_gain=-0.8,
        other_bright=0.4,
        analog_color=14.0,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare full stem remix against delta rebalance on the original mix."
    )
    parser.add_argument("input_wav", help="Path to source WAV/AIFF/audio file.")
    parser.add_argument("--model", default="htdemucs", help="Demucs model name.")
    parser.add_argument("--stems-dir", help="Reuse an existing Demucs stems folder.")
    parser.add_argument("--output-dir", help="Where to write the research run folder.")
    parser.add_argument("--preset", choices=["standard", "gentle", "balanced"], default="balanced")
    parser.add_argument(
        "--skip-final-master",
        action="store_true",
        help="Export unmastered full/delta candidates.",
    )
    return parser


def _case_args(case: RebalanceCase) -> SimpleNamespace:
    return SimpleNamespace(
        vocal_gain=case.vocal_gain,
        vocal_deharsh=case.vocal_deharsh,
        vocal_width=case.vocal_width,
        drums_gain=case.drums_gain,
        drums_punch=case.drums_punch,
        bass_gain=case.bass_gain,
        other_gain=case.other_gain,
        other_bright=case.other_bright,
        analog_color=case.analog_color,
    )


def _format_metrics(path: Path) -> str:
    audio, sample_rate = read_audio(str(path))
    analysis = analyze_track(audio, sample_rate)
    return (
        f"LUFS {analysis.lufs:.2f}, TP {analysis.true_peak:.2f}, "
        f"Crest {analysis.crest:.2f}, LRA {analysis.lra:.2f}"
    )


def _write_output(
    out_path: Path,
    candidate,
    candidate_sample_rate: int,
    target_sample_rate: int,
    preset: str,
    skip_final_master: bool,
) -> None:
    if skip_final_master:
        output = candidate
        output_sample_rate = candidate_sample_rate
    else:
        output, _before, _strategy, _after, _stats = run_mastering_pipeline(
            candidate,
            candidate_sample_rate,
            preset=preset,
        )
        output_sample_rate = candidate_sample_rate
    output = _resample_audio(output, output_sample_rate, target_sample_rate)
    write_audio(str(out_path), output, target_sample_rate)


def _write_guide(run_dir: Path, input_path: Path, output_files: list[tuple[RebalanceCase, Path, Path]]) -> None:
    lines = [
        "Инструкция по сравнению full-remix и delta-rebalance",
        "",
        f"Исходный файл: {input_path}",
        "",
        "Цель теста:",
        "Проверить, что лучше для продукта:",
        "- full: полностью собрать трек из обработанных stem-ов;",
        "- delta: оставить оригинальный микс основой и добавить только небольшие изменения от stem-ов.",
        "",
        "Гипотеза:",
        "Delta должен меньше тащить артефакты разделения, особенно из грязного music/background stem-а.",
        "",
        "Как слушать:",
        "1. Сначала послушай original.wav.",
        "2. Для каждого кейса сравни файл *_full.wav и *_delta.wav.",
        "3. Не выбирай просто самый яркий файл. Выбирай тот, где меньше разрушения и цифровой грязи.",
        "",
        "Файлы:",
        f"- original.wav: {_format_metrics(run_dir / 'original.wav')}",
    ]
    for case, full_path, delta_path in output_files:
        lines.append(f"- {full_path.name}: {case.label}. full. ({_format_metrics(full_path)})")
        lines.append(f"- {delta_path.name}: {case.label}. delta. ({_format_metrics(delta_path)})")
    lines.extend(
        [
            "",
            "Заметки:",
            "- full или delta чаще звучит естественнее:",
            "- где меньше артефактов:",
            "- лучший файл:",
            "- худший файл:",
            "- комментарии:",
        ]
    )
    (run_dir / "REBALANCE_MODE_GUIDE.txt").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_wav).resolve()
    target_sample_rate = sf.info(input_path).samplerate

    if args.output_dir:
        run_dir = Path(args.output_dir).resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path.cwd() / "research_runs" / f"{input_path.stem}_rebalance_modes_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, run_dir / "original.wav")

    if args.stems_dir:
        stems_dir = Path(args.stems_dir).resolve()
    else:
        stems_dir = _run_demucs(input_path, run_dir / "generated_stems", args.model)

    stems, stem_sample_rate = _load_stems(stems_dir)
    output_files: list[tuple[RebalanceCase, Path, Path]] = []
    for case in CASES:
        case_args = _case_args(case)

        full_candidate = _process_stems(stems, stem_sample_rate, case_args)
        full_path = run_dir / f"{case.slug}_full.wav"
        _write_output(
            full_path,
            full_candidate,
            stem_sample_rate,
            target_sample_rate,
            args.preset,
            args.skip_final_master,
        )

        delta_candidate, delta_sample_rate = _delta_rebalance_mix(
            input_path,
            stems,
            stem_sample_rate,
            case_args,
        )
        delta_path = run_dir / f"{case.slug}_delta.wav"
        _write_output(
            delta_path,
            delta_candidate,
            delta_sample_rate,
            target_sample_rate,
            args.preset,
            args.skip_final_master,
        )

        output_files.append((case, full_path, delta_path))
        print(f"Wrote {full_path}")
        print(f"Wrote {delta_path}")

    _write_guide(run_dir, input_path, output_files)
    print(f"Rebalance mode comparison ready: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

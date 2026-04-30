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
class Variant:
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


VARIANTS = (
    Variant(
        slug="00_stem_lab_baseline",
        label="Базовая stem-версия",
        purpose="Разделение на stem-ы, обратная сборка и финальный мастеринг без дополнительных правок.",
    ),
    Variant(
        slug="01_vocal_clearer",
        label="Вокал понятнее",
        purpose="Проверяем, помогает ли чуть более громкий и менее резкий вокал.",
        vocal_gain=1.5,
        vocal_deharsh=45.0,
        analog_color=10.0,
    ),
    Variant(
        slug="02_drums_stronger",
        label="Барабаны плотнее",
        purpose="Проверяем, делает ли более плотная группа барабанов трек лучше.",
        drums_punch=45.0,
        analog_color=10.0,
    ),
    Variant(
        slug="03_less_bass_brighter_music",
        label="Меньше баса, ярче музыка",
        purpose="Проверяем, помогает ли убрать низовую муть и очень мягко добавить ясности музыкальному фону.",
        bass_gain=-1.5,
        other_bright=0.5,
        analog_color=10.0,
    ),
    Variant(
        slug="04_balanced_repair",
        label="Сбалансированная правка",
        purpose="Комбинированная умеренная правка: вокал, барабаны, бас, музыкальный фон и окрас.",
        vocal_gain=1.2,
        vocal_deharsh=40.0,
        drums_punch=30.0,
        bass_gain=-0.8,
        other_bright=0.5,
        analog_color=18.0,
    ),
)


FOCUSED_VARIANTS = (
    Variant(
        slug="00_previous_best_balanced_repair",
        label="Предыдущий лучший вариант",
        purpose="Повтор варианта 04_balanced_repair из первого теста как точка сравнения.",
        vocal_gain=1.2,
        vocal_deharsh=40.0,
        drums_punch=30.0,
        bass_gain=-0.8,
        other_bright=0.5,
        analog_color=18.0,
    ),
    Variant(
        slug="01_balanced_repair_soft",
        label="Мягче и осторожнее",
        purpose="Проверяем, не станет ли приятнее при менее яркой и менее плотной обработке.",
        vocal_gain=0.9,
        vocal_deharsh=35.0,
        drums_punch=22.0,
        bass_gain=-0.6,
        other_bright=0.4,
        analog_color=14.0,
    ),
    Variant(
        slug="02_more_deharsh",
        label="Больше борьбы с песком",
        purpose="Проверяем, можно ли сильнее приглушить вокальный песок без потери приятности.",
        vocal_gain=1.1,
        vocal_deharsh=65.0,
        drums_punch=28.0,
        bass_gain=-0.8,
        other_bright=0.4,
        analog_color=16.0,
    ),
    Variant(
        slug="03_less_bass_focus",
        label="Меньше басовой мути",
        purpose="Проверяем, помогает ли чуть сильнее прибрать бас и оставить вокал впереди без сильного касания фона.",
        vocal_gain=1.2,
        vocal_deharsh=45.0,
        drums_punch=28.0,
        bass_gain=-1.4,
        other_bright=0.4,
        analog_color=16.0,
    ),
    Variant(
        slug="04_more_analog_color",
        label="Больше аналогового окраса",
        purpose="Проверяем, делает ли более сильный общий окрас трек приятнее или добавляет грязь.",
        vocal_gain=1.1,
        vocal_deharsh=45.0,
        drums_punch=28.0,
        bass_gain=-0.8,
        other_bright=0.4,
        analog_color=30.0,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a listening pack of stem-aware mastering variants."
    )
    parser.add_argument("input_wav", help="Path to source WAV/AIFF/audio file.")
    parser.add_argument("--model", default="htdemucs", help="Demucs model name.")
    parser.add_argument("--stems-dir", help="Reuse an existing Demucs stems folder.")
    parser.add_argument("--output-dir", help="Where to write the research run folder.")
    parser.add_argument("--preset", choices=["standard", "gentle", "balanced"], default="balanced")
    parser.add_argument(
        "--mix-mode",
        choices=["delta", "full"],
        default="delta",
        help="delta keeps original mix as base; full rebuilds the whole track from stems.",
    )
    parser.add_argument(
        "--variant-set",
        choices=["broad", "focused"],
        default="broad",
        help="broad explores different ideas; focused refines the current best balanced repair.",
    )
    parser.add_argument(
        "--skip-final-master",
        action="store_true",
        help="Export only processed stem remixes.",
    )
    return parser


def _variant_args(variant: Variant) -> SimpleNamespace:
    return SimpleNamespace(
        vocal_gain=variant.vocal_gain,
        vocal_deharsh=variant.vocal_deharsh,
        vocal_width=variant.vocal_width,
        drums_gain=variant.drums_gain,
        drums_punch=variant.drums_punch,
        bass_gain=variant.bass_gain,
        other_gain=variant.other_gain,
        other_bright=variant.other_bright,
        analog_color=variant.analog_color,
    )


def _format_metrics(path: Path) -> str:
    audio, sample_rate = read_audio(str(path))
    analysis = analyze_track(audio, sample_rate)
    return (
        f"LUFS {analysis.lufs:.2f}, TP {analysis.true_peak:.2f}, "
        f"Crest {analysis.crest:.2f}, LRA {analysis.lra:.2f}"
    )


def _write_guide(run_dir: Path, input_path: Path, outputs: list[tuple[Variant, Path]]) -> None:
    lines = [
        "Инструкция по прослушиванию stem-вариантов",
        "",
        f"Исходный файл: {input_path}",
        "",
        "Как слушать:",
        "1. Сначала послушай original.wav.",
        "2. Потом послушай вариант 00: это базовая точка сравнения.",
        "3. Затем сравни остальные варианты.",
        "4. Не оценивай отдельные stem-ы как студийные дорожки. Важно, стал ли лучше полный микс.",
        "",
        "Простые вопросы:",
        "- Вокал стал приятнее или раздражающим?",
        "- Трек стал яснее или тоньше/хуже?",
        "- Барабаны стали сильнее или грязнее?",
        "- Появились ли новые цифровые артефакты?",
        "- Какой файл первым хотелось бы показать заказчику?",
        "- Если это focused-пак: какой вариант лучше предыдущего победителя 00?",
        "",
        "Файлы:",
        f"- original.wav: {_format_metrics(run_dir / 'original.wav')}",
    ]
    for variant, path in outputs:
        lines.append(f"- {path.name}: {variant.label}. {variant.purpose} ({_format_metrics(path)})")
    lines.extend(
        [
            "",
            "Заметки:",
            "- лучший файл:",
            "- худший файл:",
            "- комментарии:",
        ]
    )
    (run_dir / "LISTENING_GUIDE.txt").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_wav).resolve()
    target_sample_rate = sf.info(input_path).samplerate

    if args.output_dir:
        run_dir = Path(args.output_dir).resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path.cwd() / "research_runs" / f"{input_path.stem}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.stems_dir:
        stems_dir = Path(args.stems_dir).resolve()
    else:
        stems_root = run_dir / "stems"
        stems_dir = _run_demucs(input_path, stems_root, args.model)

    shutil.copy2(input_path, run_dir / "original.wav")
    stems, sample_rate = _load_stems(stems_dir)
    variants = FOCUSED_VARIANTS if args.variant_set == "focused" else VARIANTS

    outputs: list[tuple[Variant, Path]] = []
    for variant in variants:
        variant_args = _variant_args(variant)
        if args.mix_mode == "delta":
            remix, remix_sample_rate = _delta_rebalance_mix(
                input_path,
                stems,
                sample_rate,
                variant_args,
            )
        else:
            remix = _process_stems(stems, sample_rate, variant_args)
            remix_sample_rate = sample_rate
        if args.skip_final_master:
            output = remix
            output_sample_rate = remix_sample_rate
        else:
            output, _before, _strategy, _after, _stats = run_mastering_pipeline(
                remix,
                remix_sample_rate,
                preset=args.preset,
            )
            output_sample_rate = remix_sample_rate
        output = _resample_audio(output, output_sample_rate, target_sample_rate)
        out_path = run_dir / f"{variant.slug}.wav"
        write_audio(str(out_path), output, target_sample_rate)
        outputs.append((variant, out_path))
        print(f"Wrote {out_path}")

    _write_guide(run_dir, input_path, outputs)
    print(f"Listening pack ready: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

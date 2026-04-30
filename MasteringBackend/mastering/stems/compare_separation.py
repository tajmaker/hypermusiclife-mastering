import argparse
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from mastering.domain.analyzer import analyze_track
from mastering.stems.stem_lab import STEM_NAMES, _load_stems, _resample_audio, _run_demucs
from mastering.storage.audio_io import read_audio, write_audio


DEFAULT_MODELS = ("htdemucs",)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a listening pack for comparing source separation quality."
    )
    parser.add_argument("input_wav", help="Path to source WAV/AIFF/audio file.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="Demucs model names to compare, e.g. htdemucs htdemucs_ft mdx_extra.",
    )
    parser.add_argument("--output-dir", help="Where to write the comparison folder.")
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reuse model stems in the output folder when they already exist.",
    )
    return parser


def _match_lengths(stems: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    length = min(audio.shape[0] for audio in stems.values())
    return {name: audio[:length] for name, audio in stems.items()}


def _raw_remix(stems: dict[str, np.ndarray]) -> np.ndarray:
    matched = _match_lengths(stems)
    remix = sum(matched[name] for name in STEM_NAMES)
    peak = float(np.max(np.abs(remix)))
    if peak > 0.98:
        remix = remix * (0.98 / peak)
    return remix.astype(np.float32, copy=False)


def _format_metrics(path: Path) -> str:
    audio, sample_rate = read_audio(str(path))
    analysis = analyze_track(audio, sample_rate)
    return (
        f"LUFS {analysis.lufs:.2f}, TP {analysis.true_peak:.2f}, "
        f"Crest {analysis.crest:.2f}, LRA {analysis.lra:.2f}"
    )


def _copy_stems(stems_dir: Path, model_dir: Path) -> Path:
    out_dir = model_dir / "stems"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in STEM_NAMES:
        shutil.copy2(stems_dir / f"{name}.wav", out_dir / f"{name}.wav")
    return out_dir


def _write_guide(run_dir: Path, input_path: Path, model_names: list[str]) -> None:
    lines = [
        "Инструкция по сравнению качества разделения",
        "",
        f"Исходный файл: {input_path}",
        "",
        "Цель теста:",
        "Проверить не красоту мастеринга, а качество разделения трека на части.",
        "Нас интересует, можно ли отдельно управлять vocals / drums / bass / other",
        "и затем собрать трек обратно без заметного разрушения звука.",
        "",
        "Как слушать:",
        "1. Сначала послушай original.wav.",
        "2. Для каждой модели послушай raw_remix.wav. Это обратная сборка stem-ов без мастеринг-украшений.",
        "3. Потом открой папку stems и послушай vocals/drums/bass/other.",
        "4. Solo-stem не обязан звучать как студийная дорожка. Главное: насколько он управляемый и насколько мало в нём чужих частей.",
        "",
        "На что обращать внимание:",
        "- vocals.wav: вокал цельный или рваный? много ли музыки просачивается внутрь?",
        "- drums.wav: барабаны отделены или вместе с ними сильно качает вокал/музыка?",
        "- bass.wav: бас читается или там много общей каши?",
        "- other.wav: инструменты есть, но не забирает ли other слишком много вокала?",
        "- raw_remix.wav: после разборки и сборки трек похож на исходник или появились фазовые/водяные артефакты?",
        "",
        "Файлы:",
        f"- original.wav: {_format_metrics(run_dir / 'original.wav')}",
    ]
    for model_name in model_names:
        remix = run_dir / model_name / "raw_remix.wav"
        lines.append(f"- {model_name}/raw_remix.wav: {_format_metrics(remix)}")
    lines.extend(
        [
            "",
            "Заметки:",
            "- лучшая модель разделения:",
            "- худшая модель разделения:",
            "- какой stem чаще всего проблемный:",
            "- комментарии:",
        ]
    )
    (run_dir / "SEPARATION_GUIDE.txt").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_wav).resolve()
    target_sample_rate = sf.info(input_path).samplerate

    if args.output_dir:
        run_dir = Path(args.output_dir).resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path.cwd() / "research_runs" / f"{input_path.stem}_separation_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, run_dir / "original.wav")

    completed_models: list[str] = []
    for model_name in args.models:
        model_dir = run_dir / model_name
        copied_stems_dir = model_dir / "stems"
        if args.reuse_existing and all((copied_stems_dir / f"{name}.wav").exists() for name in STEM_NAMES):
            stems_dir = copied_stems_dir
        else:
            generated_dir = _run_demucs(input_path, model_dir / "generated", model_name)
            stems_dir = _copy_stems(generated_dir, model_dir)

        stems, stem_sample_rate = _load_stems(stems_dir)
        remix = _raw_remix(stems)
        remix = _resample_audio(remix, stem_sample_rate, target_sample_rate)
        write_audio(str(model_dir / "raw_remix.wav"), remix, target_sample_rate)
        completed_models.append(model_name)
        print(f"Wrote separation comparison for {model_name}: {model_dir}")

    _write_guide(run_dir, input_path, completed_models)
    print(f"Separation comparison ready: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

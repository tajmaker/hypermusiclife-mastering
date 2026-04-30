import argparse
import os
import shutil
import uuid
from pathlib import Path
from typing import Mapping

import numpy as np
from pedalboard import Compressor, HighShelfFilter, Pedalboard
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfiltfilt

from mastering.contracts.decision import PresetName
from mastering.orchestration.pipeline import run_mastering_pipeline
from mastering.storage.audio_io import read_audio, write_audio
from mastering.utils.audio_math import apply_gain_linear, ensure_2d


STEM_NAMES = ("vocals", "drums", "bass", "other")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Experimental stem-aware mastering lab using Demucs separation."
    )
    parser.add_argument("input_wav", help="Path to source WAV/AIFF/audio file.")
    parser.add_argument("output_wav", help="Path to mastered output WAV.")
    parser.add_argument("--model", default="htdemucs", help="Demucs model name.")
    parser.add_argument(
        "--stems-dir",
        help="Reuse an existing Demucs stems folder, or write separated stems here.",
    )
    parser.add_argument(
        "--keep-stems",
        action="store_true",
        help="Keep generated stems when --stems-dir is not provided.",
    )
    parser.add_argument("--preset", choices=["standard", "gentle", "balanced"], default="balanced")
    parser.add_argument("--vocal-gain", type=float, default=0.0, help="Vocal gain in dB.")
    parser.add_argument("--vocal-deharsh", type=float, default=0.0, help="0..100 upper-mid attenuation.")
    parser.add_argument("--vocal-width", type=float, default=0.0, help="-100..100 vocal side width change.")
    parser.add_argument("--drums-gain", type=float, default=0.0, help="Drums gain in dB.")
    parser.add_argument("--drums-punch", type=float, default=0.0, help="0..100 drum compression/presence.")
    parser.add_argument("--bass-gain", type=float, default=0.0, help="Bass gain in dB.")
    parser.add_argument(
        "--music-gain",
        "--other-gain",
        dest="other_gain",
        type=float,
        default=0.0,
        help="Music/background gain in dB.",
    )
    parser.add_argument(
        "--music-bright",
        "--other-bright",
        dest="other_bright",
        type=float,
        default=0.0,
        help="Music/background high shelf gain in dB. Keep this subtle; it is not a clean synth stem.",
    )
    parser.add_argument("--analog-color", type=float, default=0.0, help="0..100 soft saturation before final mastering.")
    parser.add_argument(
        "--skip-final-master",
        action="store_true",
        help="Export the stem remix without running the final mastering pipeline.",
    )
    parser.add_argument(
        "--mix-mode",
        choices=["full", "delta"],
        default="delta",
        help="full rebuilds from stems; delta adds only stem-derived changes back onto the original mix.",
    )
    return parser


def _run_demucs(input_path: Path, output_root: Path, model: str) -> Path:
    cache_root = Path.cwd() / "stem_runs" / "_model_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_HOME", str(cache_root / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root / "xdg"))

    import torch
    from demucs.apply import apply_model
    from demucs.audio import convert_audio
    from demucs.pretrained import get_model

    demucs_model = get_model(name=model)
    demucs_model.cpu()
    demucs_model.eval()

    audio, source_sr = read_audio(str(input_path))
    wav = torch.from_numpy(audio.T.astype(np.float32, copy=False))
    wav = convert_audio(wav, source_sr, demucs_model.samplerate, demucs_model.audio_channels)

    ref = wav.mean(0)
    wav -= ref.mean()
    wav /= ref.std()
    with torch.no_grad():
        sources = apply_model(
            demucs_model,
            wav[None],
            device="cpu",
            shifts=1,
            split=True,
            overlap=0.25,
            progress=True,
            num_workers=0,
        )[0]
    sources *= ref.std()
    sources += ref.mean()

    track_dir = output_root / model / input_path.stem
    track_dir.mkdir(parents=True, exist_ok=True)
    for source, name in zip(sources, demucs_model.sources):
        stem_audio = source.cpu().numpy().T.astype(np.float32, copy=False)
        write_audio(str(track_dir / f"{name}.wav"), stem_audio, demucs_model.samplerate)
    return track_dir


def _load_stems(stems_dir: Path) -> tuple[dict[str, np.ndarray], int]:
    stems: dict[str, np.ndarray] = {}
    sample_rate: int | None = None
    for name in STEM_NAMES:
        path = stems_dir / f"{name}.wav"
        if not path.exists():
            raise FileNotFoundError(f"Expected Demucs stem is missing: {path}")
        audio, sr = read_audio(str(path))
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            raise ValueError(f"Sample rate mismatch in stem {path}: {sr} != {sample_rate}")
        stems[name] = ensure_2d(audio)
    if sample_rate is None:
        raise ValueError(f"No stems found in: {stems_dir}")
    return stems, sample_rate


def _match_lengths(stems: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    length = min(audio.shape[0] for audio in stems.values())
    return {name: audio[:length] for name, audio in stems.items()}


def _resample_audio(audio: np.ndarray, from_sample_rate: int, to_sample_rate: int) -> np.ndarray:
    if from_sample_rate == to_sample_rate:
        return audio
    gcd = np.gcd(from_sample_rate, to_sample_rate)
    return resample_poly(
        audio,
        up=to_sample_rate // gcd,
        down=from_sample_rate // gcd,
        axis=0,
    ).astype(np.float32, copy=False)


def _apply_width(audio: np.ndarray, amount: float) -> np.ndarray:
    audio = ensure_2d(audio)
    if audio.shape[1] < 2 or abs(amount) < 1e-6:
        return audio
    width = 1.0 + float(np.clip(amount, -100.0, 100.0)) / 100.0
    left = audio[:, 0]
    right = audio[:, 1]
    mid = 0.5 * (left + right)
    side = 0.5 * (left - right) * width
    return np.column_stack((mid + side, mid - side)).astype(np.float32, copy=False)


def _deharsh(audio: np.ndarray, sample_rate: int, amount: float) -> np.ndarray:
    amount = float(np.clip(amount, 0.0, 100.0))
    if amount <= 0.0:
        return audio
    low = 2500.0 / (sample_rate * 0.5)
    high = min(8500.0 / (sample_rate * 0.5), 0.98)
    sos = butter(4, (low, high), btype="bandpass", output="sos")
    band = sosfiltfilt(sos, audio, axis=0)
    attenuation = 1.0 - (amount / 100.0) * 0.55
    return (audio - band + band * attenuation).astype(np.float32, copy=False)


def _soft_saturate(audio: np.ndarray, amount: float) -> np.ndarray:
    amount = float(np.clip(amount, 0.0, 100.0))
    if amount <= 0.0:
        return audio
    drive = 1.0 + amount / 35.0
    wet = np.tanh(audio * drive) / np.tanh(drive)
    mix = min(0.35, amount / 220.0)
    return ((1.0 - mix) * audio + mix * wet).astype(np.float32, copy=False)


def _process_stems(stems: Mapping[str, np.ndarray], sample_rate: int, args: argparse.Namespace) -> np.ndarray:
    processed = _match_lengths(stems)

    processed["vocals"] = apply_gain_linear(processed["vocals"], args.vocal_gain)
    processed["vocals"] = _deharsh(processed["vocals"], sample_rate, args.vocal_deharsh)
    processed["vocals"] = _apply_width(processed["vocals"], args.vocal_width)

    processed["drums"] = apply_gain_linear(processed["drums"], args.drums_gain)
    processed["bass"] = apply_gain_linear(processed["bass"], args.bass_gain)
    processed["other"] = apply_gain_linear(processed["other"], args.other_gain)

    if args.drums_punch > 0.0:
        amount = float(np.clip(args.drums_punch, 0.0, 100.0)) / 100.0
        board = Pedalboard(
            [
                Compressor(
                    threshold_db=-18.0 + amount * 5.0,
                    ratio=1.3 + amount * 1.7,
                    attack_ms=12.0,
                    release_ms=120.0,
                )
            ]
        )
        processed["drums"] = board(processed["drums"], sample_rate)

    if abs(args.other_bright) > 1e-6:
        gain = float(np.clip(args.other_bright, -4.0, 4.0))
        board = Pedalboard([HighShelfFilter(cutoff_frequency_hz=6500.0, gain_db=gain)])
        processed["other"] = board(processed["other"], sample_rate)

    remix = sum(processed[name] for name in STEM_NAMES)
    peak = float(np.max(np.abs(remix)))
    if peak > 0.98:
        remix = remix * (0.98 / peak)
    return _soft_saturate(remix.astype(np.float32, copy=False), args.analog_color)


def _raw_stem_remix(stems: Mapping[str, np.ndarray]) -> np.ndarray:
    matched = _match_lengths(stems)
    remix = sum(matched[name] for name in STEM_NAMES)
    peak = float(np.max(np.abs(remix)))
    if peak > 0.98:
        remix = remix * (0.98 / peak)
    return remix.astype(np.float32, copy=False)


def _delta_rebalance_mix(
    input_path: Path,
    stems: Mapping[str, np.ndarray],
    stem_sample_rate: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, int]:
    original, original_sample_rate = read_audio(str(input_path))
    raw_remix = _raw_stem_remix(stems)
    processed_remix = _process_stems(stems, stem_sample_rate, args)
    length = min(raw_remix.shape[0], processed_remix.shape[0])
    delta = processed_remix[:length] - raw_remix[:length]
    delta = _resample_audio(delta, stem_sample_rate, original_sample_rate)

    out_len = min(original.shape[0], delta.shape[0])
    output = original[:out_len] + delta[:out_len]
    peak = float(np.max(np.abs(output)))
    if peak > 0.98:
        output = output * (0.98 / peak)
    return output.astype(np.float32, copy=False), original_sample_rate


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_wav).resolve()
    output_path = Path(args.output_wav).resolve()
    target_sample_rate = sf.info(input_path).samplerate

    generated_root: Path | None = None
    try:
        if args.stems_dir:
            stems_dir = Path(args.stems_dir).resolve()
            if not all((stems_dir / f"{name}.wav").exists() for name in STEM_NAMES):
                stems_dir = _run_demucs(input_path, stems_dir, args.model)
        else:
            generated_root = Path.cwd() / "stem_runs" / f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
            generated_root.mkdir(parents=True, exist_ok=True)
            stems_dir = _run_demucs(input_path, generated_root, args.model)

        stems, sample_rate = _load_stems(stems_dir)
        if args.mix_mode == "delta":
            candidate, candidate_sample_rate = _delta_rebalance_mix(
                input_path,
                stems,
                sample_rate,
                args,
            )
        else:
            candidate = _process_stems(stems, sample_rate, args)
            candidate_sample_rate = sample_rate

        if args.skip_final_master:
            output = candidate
            output_sample_rate = candidate_sample_rate
        else:
            output, _before, _strategy, _after, _stats = run_mastering_pipeline(
                candidate,
                candidate_sample_rate,
                preset=args.preset,
            )
            output_sample_rate = candidate_sample_rate
        output = _resample_audio(output, output_sample_rate, target_sample_rate)
        write_audio(str(output_path), output, target_sample_rate)
        print(f"Stem lab output written: {output_path}")
        if generated_root is not None and args.keep_stems:
            keep_path = output_path.with_suffix("")
            keep_path = keep_path.parent / f"{keep_path.name}_stems"
            shutil.copytree(stems_dir, keep_path, dirs_exist_ok=True)
            print(f"Generated stems kept at: {keep_path}")
        return 0
    finally:
        if generated_root is not None and not args.keep_stems:
            shutil.rmtree(generated_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

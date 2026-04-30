import argparse
from pathlib import Path

import numpy as np

from mastering.domain.analyzer import analyze_track
from mastering.stems.stem_lab import _resample_audio
from mastering.storage.audio_io import read_audio
from mastering.utils.audio_math import ensure_2d, lin_to_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a simple audio similarity report against a reference file."
    )
    parser.add_argument("reference_wav", help="Reference WAV/AIFF/audio file.")
    parser.add_argument("candidates_dir", help="Folder containing candidate WAV files.")
    parser.add_argument("--pattern", default="*.wav", help="Candidate glob pattern.")
    parser.add_argument("--output", default="SIMILARITY_REPORT.txt", help="Output report filename.")
    return parser


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(audio, dtype=np.float64) ** 2) + 1e-12))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    a = a - float(np.mean(a))
    b = b - float(np.mean(b))
    denom = float(np.sqrt(np.sum(a * a) * np.sum(b * b)) + 1e-12)
    return float(np.sum(a * b) / denom)


def _band_db(audio: np.ndarray, sample_rate: int, low_hz: float, high_hz: float) -> float:
    mono = ensure_2d(audio).mean(axis=1)
    spec = np.fft.rfft(mono)
    freqs = np.fft.rfftfreq(mono.shape[0], 1.0 / sample_rate)
    idx = (freqs >= low_hz) & (freqs < high_hz)
    if not np.any(idx):
        return -120.0
    power = float(np.mean(np.abs(spec[idx]) ** 2) + 1e-12)
    return lin_to_db(power)


def _compare(reference: np.ndarray, candidate: np.ndarray, sample_rate: int) -> dict[str, float]:
    length = min(reference.shape[0], candidate.shape[0])
    ref = ensure_2d(reference[:length])
    cand = ensure_2d(candidate[:length])

    # Level-match only for the residual score, so loudness changes do not dominate.
    gain = _rms(ref) / (_rms(cand) + 1e-12)
    cand_matched = cand * gain
    residual = cand_matched - ref
    residual_vs_signal_db = 20.0 * np.log10((_rms(residual) + 1e-12) / (_rms(ref) + 1e-12))

    ref_analysis = analyze_track(ref, sample_rate)
    cand_analysis = analyze_track(cand, sample_rate)

    return {
        "corr": _corr(ref, cand_matched),
        "residual_vs_signal_db": float(residual_vs_signal_db),
        "lufs_delta": cand_analysis.lufs - ref_analysis.lufs,
        "true_peak_delta": cand_analysis.true_peak - ref_analysis.true_peak,
        "lra_delta": cand_analysis.lra - ref_analysis.lra,
        "low_delta": _band_db(cand, sample_rate, 20.0, 200.0) - _band_db(ref, sample_rate, 20.0, 200.0),
        "mid_delta": _band_db(cand, sample_rate, 200.0, 4000.0) - _band_db(ref, sample_rate, 200.0, 4000.0),
        "high_delta": _band_db(cand, sample_rate, 4000.0, 20000.0) - _band_db(ref, sample_rate, 4000.0, 20000.0),
    }


def main() -> int:
    args = build_parser().parse_args()
    reference_path = Path(args.reference_wav).resolve()
    candidates_dir = Path(args.candidates_dir).resolve()
    reference, ref_sr = read_audio(str(reference_path))

    lines = [
        "Audio similarity report",
        "",
        f"Reference: {reference_path}",
        "",
        "Interpretation:",
        "- corr closer to 1.0 means more similar waveform after level matching.",
        "- residual_vs_signal_db more negative means less difference from original.",
        "- deltas near 0 mean the candidate preserved that metric.",
        "",
        "file | corr | residual dB | LUFS d | TP d | LRA d | low d | mid d | high d",
    ]

    for path in sorted(candidates_dir.glob(args.pattern)):
        if path.name == reference_path.name or path.name == args.output:
            continue
        try:
            candidate, candidate_sr = read_audio(str(path))
        except Exception:
            continue
        if candidate_sr != ref_sr:
            candidate = _resample_audio(candidate, candidate_sr, ref_sr)
        metrics = _compare(reference, candidate, ref_sr)
        lines.append(
            f"{path.name} | "
            f"{metrics['corr']:.4f} | "
            f"{metrics['residual_vs_signal_db']:.2f} | "
            f"{metrics['lufs_delta']:+.2f} | "
            f"{metrics['true_peak_delta']:+.2f} | "
            f"{metrics['lra_delta']:+.2f} | "
            f"{metrics['low_delta']:+.2f} | "
            f"{metrics['mid_delta']:+.2f} | "
            f"{metrics['high_delta']:+.2f}"
        )

    out_path = candidates_dir / args.output
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Similarity report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

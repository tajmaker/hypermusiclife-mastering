import argparse

from typing import cast

from mastering.contracts.decision import PresetName
from mastering.orchestration.pipeline import analyze_single, run_mastering_pipeline
from mastering.storage.audio_io import read_audio, write_audio
from mastering.utils.reporting import print_analysis, print_before_after, print_pair_comparison, print_strategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MasteringBackend CLI: analyzer -> decision -> processor pipeline."
    )
    parser.add_argument("input_wav", nargs="?", help="Path to input WAV/AIFF")
    parser.add_argument("output_wav", nargs="?", help="Path to output WAV")
    parser.add_argument(
        "--preset",
        choices=["standard", "gentle", "balanced"],
        default="standard",
        help="Processing profile.",
    )
    parser.add_argument("--analyze-only", action="store_true", help="Analyze one file and exit.")
    parser.add_argument(
        "--analyze-pair",
        nargs=2,
        metavar=("REF_WAV", "TEST_WAV"),
        help="Analyze and compare two files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.analyze_pair:
        ref_path, test_path = args.analyze_pair
        ref_audio, ref_sr = read_audio(ref_path)
        test_audio, test_sr = read_audio(test_path)
        if ref_sr != test_sr:
            raise SystemExit("Sample rate mismatch between reference and test files.")
        ref_analysis = analyze_single(ref_audio, ref_sr)
        test_analysis = analyze_single(test_audio, test_sr)
        print_analysis("REFERENCE", ref_analysis)
        print_analysis("TEST", test_analysis)
        print_pair_comparison(ref_analysis, test_analysis, ref_path, test_path)
        return 0

    if not args.input_wav:
        raise SystemExit("input_wav is required.")

    audio, sample_rate = read_audio(args.input_wav)
    if args.analyze_only:
        print_analysis("INPUT", analyze_single(audio, sample_rate))
        return 0

    if not args.output_wav:
        raise SystemExit("output_wav is required when processing.")

    processed, before, strategy, after, _stats = run_mastering_pipeline(
        audio=audio,
        sample_rate=sample_rate,
        preset=cast(PresetName, args.preset),
    )
    print_analysis("INPUT", before)
    print_strategy(strategy, args.preset)
    print_analysis("OUTPUT", after)
    print_before_after(before, after)
    write_audio(args.output_wav, processed, sample_rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


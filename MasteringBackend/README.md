---
title: HyperMusicLife Mastering Backend
emoji: 🎛️
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# MasteringBackend Architecture
- `mastering/api`: HTTP boundary (FastAPI stubs and future routers).
- `mastering/orchestration`: pipeline wiring and job lifecycle helpers.
- `mastering/domain/analyzer.py`: audio analysis only.
- `mastering/domain/decision_engine.py`: strategy selection only.
- `mastering/domain/processor.py`: DSP processing and safety pass only.
- `mastering/stems`: experimental stem-aware research tools.
- `mastering/storage`: audio file I/O and future S3 object storage adapter.
- `mastering/contracts`: typed dataclasses exchanged between modules.
- `mastering/utils`: reusable math/reporting helpers.
- `mastering/config.py`: single source of thresholds and runtime settings.
- `mastering/cli.py`: CLI entry point that composes modules.

## Current Research Direction

The customer problem is not only final mastering. SUNO-like tracks often need
mix repair before mastering: vocal rebalance, harsh resonance reduction, drum
punch, bass control, instrument brightness, and analog-style color.

The current hypothesis is a stem-aware pipeline:

```text
input mix
  -> source separation: vocals / drums / bass / music-background
  -> per-stem rebalance and processing
  -> remix
  -> final mastering pipeline
  -> export
```

## Stem Lab

`stem_lab` is an experimental CLI for validating that hypothesis. It uses
Demucs/HTDemucs for source separation, then applies a small set of controlled
per-stem edits before optional final mastering.

Install optional stem dependencies:

```bash
..\.venv\Scripts\pip.exe install demucs
```

From `MasteringBackend`, run:

```bash
..\.venv\Scripts\python.exe -m mastering.stems.stem_lab input.wav output.wav ^
  --vocal-gain 1.0 ^
  --vocal-deharsh 25 ^
  --drums-punch 20 ^
  --music-bright 0.5 ^
  --analog-color 15
```

Useful research flags:

- `--skip-final-master`: export only the processed stem remix.
- `--keep-stems`: keep generated stems next to the output.
- `--stems-dir path`: reuse already separated stems instead of running Demucs again.

Model weights are cached under `stem_runs/_model_cache`.
The final export is resampled back to the input file sample rate.
By default, `stem_lab` uses `--mix-mode delta`: the original mix remains the
base and only small stem-derived changes are added back. Use `--mix-mode full`
only for research comparisons.

## Listening Packs

Use `make_variants` to create a folder with several ready-to-compare versions
of one track. This is the preferred way to run non-engineer listening tests.

```bash
..\.venv\Scripts\python.exe -m mastering.stems.make_variants input.wav ^
  --stems-dir existing_stems_folder ^
  --output-dir research_runs\track_name_test
```

If `--stems-dir` is omitted, Demucs separation runs first. The output folder
contains `original.wav`, numbered variants, and `LISTENING_GUIDE.txt`.

## Separation Comparison

Use `compare_separation` when the goal is not mastering taste, but checking how
cleanly different models split and rebuild a track.

```bash
..\.venv\Scripts\python.exe -m mastering.stems.compare_separation input.wav ^
  --models htdemucs htdemucs_ft mdx_extra ^
  --output-dir research_runs\track_name_separation
```

The output contains `original.wav`, per-model `stems/`, `raw_remix.wav`, and
`SEPARATION_GUIDE.txt`.

## Rebalance Mode Comparison

Use `compare_rebalance_modes` to test whether stem edits should rebuild the
whole track (`full`) or be added back as small changes over the original mix
(`delta`).

```bash
..\.venv\Scripts\python.exe -m mastering.stems.compare_rebalance_modes input.wav ^
  --stems-dir existing_stems_folder ^
  --output-dir research_runs\track_rebalance_modes
```

The output contains paired `*_full.wav` and `*_delta.wav` files plus
`REBALANCE_MODE_GUIDE.txt`.

## Similarity Report

Use `similarity_report` to get a rough objective check of how far candidates
move away from a reference.

```bash
..\.venv\Scripts\python.exe -m mastering.stems.similarity_report original.wav research_runs\some_pack
```

This writes `SIMILARITY_REPORT.txt` with correlation, residual error, and basic
analysis deltas. It is a helper for research, not a replacement for listening.

## Rebalance Master

Use `rebalance_master` for the current production-like MVP path: one input,
one output, delta rebalance, final mastering, and a JSON report.

```bash
..\.venv\Scripts\python.exe -m mastering.stems.rebalance_master input.wav output.wav ^
  --profile safe
```

Optional flags:

- `--model mdx_extra`: current default separation model.
- `--stems-dir path`: reuse existing stems and avoid running separation again.
- `--profile safe|vocal`: choose the rebalance profile.
- `--skip-final-master`: export only delta rebalance for research.

The same path is also available as Python code:

```python
from mastering.stems.rebalance_master import process_rebalance_master

process_rebalance_master(
    "input.wav",
    "output.wav",
    profile_name="safe",
    control_overrides={
        "vocal_gain": 1.0,
        "bass_gain": -0.5,
        "music_bright": 0.4,
    },
)
```

## Stem Rebalance API

FastAPI is still a thin local wrapper, but it now exposes the current MVP
pipeline. Install API dependencies if needed:

```bash
..\.venv\Scripts\pip.exe install -e .[api]
```

Run the API from `MasteringBackend`:

```bash
..\.venv\Scripts\uvicorn.exe mastering.api.app:app --reload
```

Useful endpoints:

- `GET /api/v1/stem-rebalance/presets`: list safe preset values.
- `POST /api/v1/stem-rebalance`: process one file synchronously.

Example JSON body:

```json
{
  "input_path": "../Исходники/DEMO_92 - IN MY ZONE - POP - PAI-0102 (116BPM).wav",
  "output_path": "research_runs/api_demo.wav",
  "stems_dir": "research_runs/DEMO_92_separation_mdx_extra/mdx_extra/stems",
  "profile": "safe",
  "controls": {
    "vocal_gain": 1.0,
    "bass_gain": -0.5,
    "music_bright": 0.4
  }
}
```


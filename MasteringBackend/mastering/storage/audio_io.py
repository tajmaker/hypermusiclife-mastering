from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf

from mastering.config import SETTINGS


def read_audio(path: str) -> Tuple[np.ndarray, int]:
    audio, sample_rate = sf.read(path, always_2d=True, dtype="float32")
    if sample_rate < SETTINGS.min_sample_rate_hz:
        raise ValueError(f"Expected sample rate >= {SETTINGS.min_sample_rate_hz} Hz.")
    return audio, sample_rate


def write_audio(path: str, audio: np.ndarray, sample_rate: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sample_rate, subtype=SETTINGS.output_subtype)


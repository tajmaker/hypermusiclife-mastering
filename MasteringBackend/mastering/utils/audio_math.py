import math

import numpy as np
from scipy.signal import resample_poly


def lin_to_db(x: float, floor_db: float = -120.0) -> float:
    x = float(x)
    if x <= 0.0:
        return floor_db
    return 20.0 * math.log10(x)


def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def ensure_2d(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio[:, None]
    return audio


def to_mono(audio: np.ndarray) -> np.ndarray:
    audio = ensure_2d(audio)
    if audio.shape[1] == 1:
        return audio[:, 0]
    return audio.mean(axis=1)


def rms_dbfs(audio: np.ndarray) -> float:
    audio = np.asarray(audio, dtype=np.float64)
    rms = float(np.sqrt(np.mean(audio**2)))
    return lin_to_db(rms)


def peak_dbfs(audio: np.ndarray) -> float:
    audio = np.asarray(audio, dtype=np.float64)
    peak = float(np.max(np.abs(audio)))
    return lin_to_db(peak)


def true_peak_dbfs(audio: np.ndarray, sample_rate: int, oversample: int = 4) -> float:
    audio = ensure_2d(audio).astype(np.float64)
    if oversample <= 1:
        return peak_dbfs(audio)
    peaks = []
    for ch in range(audio.shape[1]):
        y_os = resample_poly(audio[:, ch], up=oversample, down=1)
        peaks.append(float(np.max(np.abs(y_os))))
    return lin_to_db(max(peaks))


def apply_gain_linear(audio: np.ndarray, gain_db: float) -> np.ndarray:
    if abs(gain_db) < 1e-6:
        return audio
    return audio * db_to_lin(gain_db)


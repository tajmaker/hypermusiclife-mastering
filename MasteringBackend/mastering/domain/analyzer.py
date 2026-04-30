import numpy as np
import librosa
import pyloudnorm as pyln

from mastering.config import SETTINGS
from mastering.contracts.analysis import AnalysisResult, BandEnergies
from mastering.utils.audio_math import ensure_2d, lin_to_db, rms_dbfs, to_mono, true_peak_dbfs


def analyze_track(audio: np.ndarray, sample_rate: int) -> AnalysisResult:
    audio = ensure_2d(audio)
    mono = to_mono(audio)

    meter = pyln.Meter(sample_rate)
    lufs = float(meter.integrated_loudness(mono))
    lra = float(meter.loudness_range(mono))

    tp = true_peak_dbfs(audio, sample_rate, oversample=SETTINGS.true_peak_oversample_factor)
    rms = rms_dbfs(mono)
    crest = tp - rms

    n_fft = 8192
    hop_length = 4096
    stft = librosa.stft(mono, n_fft=n_fft, hop_length=hop_length)
    mag2 = np.abs(stft) ** 2
    freqs = librosa.fft_frequencies(sr=sample_rate, n_fft=n_fft)

    def band_power(f_lo: float, f_hi: float) -> float:
        idx = (freqs >= f_lo) & (freqs < f_hi)
        if not np.any(idx):
            return 1e-12
        return float(np.mean(mag2[idx, :]) + 1e-12)

    low_p = band_power(20.0, 200.0)
    mid_p = band_power(200.0, 4000.0)
    high_p = band_power(4000.0, 20000.0)

    low_db = lin_to_db(low_p)
    mid_db = lin_to_db(mid_p)
    high_db = lin_to_db(high_p)
    low_vs_mid = low_db - mid_db
    high_vs_mid = high_db - mid_db

    if low_vs_mid > 3.0:
        spectrum_class = "bass_heavy"
    elif high_vs_mid > 3.0:
        spectrum_class = "bright"
    elif high_vs_mid < -3.0:
        spectrum_class = "dark"
    else:
        spectrum_class = "balanced"

    if lufs < -22.0:
        loudness_class = "very_quiet"
    elif lufs > -16.0:
        loudness_class = "already_loud"
    else:
        loudness_class = "moderate"

    if crest > 12.0:
        dynamics_class = "high_crest"
    elif crest < 8.0:
        dynamics_class = "low_crest"
    else:
        dynamics_class = "mid_crest"

    if audio.shape[1] == 1:
        stereo_corr = 1.0
        mid_side_ratio_db = 120.0
    else:
        left = audio[:, 0].astype(np.float64)
        right = audio[:, 1].astype(np.float64)
        if np.allclose(left, right):
            stereo_corr = 1.0
        else:
            stereo_corr = float(np.clip(np.corrcoef(left, right)[0, 1], -1.0, 1.0))
        mid = 0.5 * (left + right)
        side = 0.5 * (left - right)
        mid_rms = np.sqrt(np.mean(mid**2) + 1e-12)
        side_rms = np.sqrt(np.mean(side**2) + 1e-12)
        mid_side_ratio_db = lin_to_db(mid_rms / side_rms)

    return AnalysisResult(
        lufs=lufs,
        true_peak=tp,
        rms=rms,
        crest=crest,
        lra=lra,
        band_energies=BandEnergies(
            low_db=low_db,
            mid_db=mid_db,
            high_db=high_db,
            low_vs_mid_db=low_vs_mid,
            high_vs_mid_db=high_vs_mid,
        ),
        spectrum_class=spectrum_class,
        loudness_class=loudness_class,
        dynamics_class=dynamics_class,
        stereo_corr=stereo_corr,
        mid_side_ratio_db=mid_side_ratio_db,
    )


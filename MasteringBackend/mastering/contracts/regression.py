from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TrackRunMetrics:
    track_name: str
    lufs_before: float
    lufs_after: float
    true_peak_before: float
    true_peak_after: float
    crest_before: float
    crest_after: float
    lra_before: float
    lra_after: float
    limiter_avg_gr_db: float
    spectral_shift_low_db: float
    spectral_shift_mid_db: float
    spectral_shift_high_db: float
    safety_flags: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["safety_flags"] = list(self.safety_flags)
        return data

    @staticmethod
    def from_dict(data: dict) -> "TrackRunMetrics":
        return TrackRunMetrics(
            track_name=data["track_name"],
            lufs_before=float(data["lufs_before"]),
            lufs_after=float(data["lufs_after"]),
            true_peak_before=float(data["true_peak_before"]),
            true_peak_after=float(data["true_peak_after"]),
            crest_before=float(data["crest_before"]),
            crest_after=float(data["crest_after"]),
            lra_before=float(data["lra_before"]),
            lra_after=float(data["lra_after"]),
            limiter_avg_gr_db=float(data["limiter_avg_gr_db"]),
            spectral_shift_low_db=float(data["spectral_shift_low_db"]),
            spectral_shift_mid_db=float(data["spectral_shift_mid_db"]),
            spectral_shift_high_db=float(data["spectral_shift_high_db"]),
            safety_flags=tuple(data.get("safety_flags", [])),
        )


try:
    from pydantic import BaseModel, Field
    from typing import Literal
except Exception:  # pragma: no cover
    BaseModel = object
    Field = None


if Field is not None:
    StemName = Literal["vocals", "drums", "bass", "other"]
    EqBandType = Literal["bell", "lowShelf", "highShelf", "highPass", "lowPass"]

    class EqBand(BaseModel):
        id: str
        type: EqBandType = "bell"
        frequency_hz: float = Field(ge=20.0, le=20000.0)
        gain_db: float = Field(default=0.0, ge=-24.0, le=24.0)
        q: float = Field(default=1.0, ge=0.1, le=24.0)
        enabled: bool = True


    class StemProcessing(BaseModel):
        gain_db: float = Field(default=0.0, ge=-60.0, le=12.0)
        muted: bool = False
        solo: bool = False
        eq_bands: list[EqBand] = Field(default_factory=list, max_items=8)


    class MixProject(BaseModel):
        mode: Literal["delta", "full"] = "delta"
        stems: dict[StemName, StemProcessing]


    class RebalanceControls(BaseModel):
        vocal_gain: float | None = Field(default=None, ge=-60.0, le=12.0)
        vocal_deharsh: float | None = Field(default=None, ge=0.0, le=100.0)
        vocal_width: float | None = Field(default=None, ge=0.0, le=100.0)
        drums_gain: float | None = Field(default=None, ge=-60.0, le=12.0)
        drums_punch: float | None = Field(default=None, ge=0.0, le=100.0)
        bass_gain: float | None = Field(default=None, ge=-60.0, le=12.0)
        music_gain: float | None = Field(default=None, ge=-60.0, le=12.0)
        music_bright: float | None = Field(default=None, ge=-3.0, le=3.0)
        analog_color: float | None = Field(default=None, ge=0.0, le=100.0)

        def enabled(self) -> dict[str, float]:
            return {name: float(value) for name, value in self.dict(exclude_none=True).items()}


    class StemRebalanceRequest(BaseModel):
        input_path: str
        output_path: str
        stems_dir: str | None = None
        model: str = "mdx_extra"
        profile: str = "safe"
        mastering_preset: str = "balanced"
        report_path: str | None = None
        skip_final_master: bool = False
        keep_stems: bool = False
        mix_mode: Literal["delta", "full"] = "delta"
        controls: RebalanceControls | None = None
        mix_project: MixProject | None = None


    class RenderRequest(BaseModel):
        profile: str = "safe"
        mastering_preset: str = "balanced"
        controls: RebalanceControls | None = None
        mix_project: MixProject | None = None
        skip_final_master: bool = False
        mix_mode: Literal["delta", "full"] = "delta"

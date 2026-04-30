try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    BaseModel = object
    Field = None


if Field is not None:

    class RebalanceControls(BaseModel):
        vocal_gain: float | None = Field(default=None, ge=-6.0, le=6.0)
        vocal_deharsh: float | None = Field(default=None, ge=0.0, le=100.0)
        vocal_width: float | None = Field(default=None, ge=0.0, le=100.0)
        drums_gain: float | None = Field(default=None, ge=-6.0, le=6.0)
        drums_punch: float | None = Field(default=None, ge=0.0, le=100.0)
        bass_gain: float | None = Field(default=None, ge=-6.0, le=6.0)
        music_gain: float | None = Field(default=None, ge=-6.0, le=6.0)
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
        controls: RebalanceControls | None = None


    class RenderRequest(BaseModel):
        profile: str = "safe"
        mastering_preset: str = "balanced"
        controls: RebalanceControls | None = None
        skip_final_master: bool = False

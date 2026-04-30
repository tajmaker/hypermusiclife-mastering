from pathlib import Path

try:
    from fastapi import APIRouter, File, HTTPException, UploadFile
    from fastapi.responses import FileResponse
except Exception:  # pragma: no cover
    APIRouter = None

if APIRouter is not None:
    from mastering.api.schemas.tracks import RenderRequest, StemRebalanceRequest
    from mastering.application.track_jobs import RenderParams, STEM_NAMES, TrackJobService
    from mastering.stems.rebalance_master import PRESETS, process_rebalance_master

    router = APIRouter(tags=["mastering"])
    track_jobs = TrackJobService(root_dir=Path("hosted_runs"), max_workers=1)

    @router.post("/jobs")
    async def create_mastering_job() -> dict:
        return {"message": "legacy stub: use /tracks"}

    @router.get("/jobs/{job_id}")
    async def get_mastering_job(job_id: str) -> dict:
        return {"job_id": job_id, "message": "legacy stub: use /tracks/{track_id}"}

    @router.get("/stem-rebalance/presets")
    async def list_stem_rebalance_presets() -> dict:
        return {
            name: {
                "description": preset.description,
                "controls": {
                    "vocal_gain": preset.vocal_gain,
                    "vocal_deharsh": preset.vocal_deharsh,
                    "vocal_width": preset.vocal_width,
                    "drums_gain": preset.drums_gain,
                    "drums_punch": preset.drums_punch,
                    "bass_gain": preset.bass_gain,
                    "music_gain": preset.music_gain,
                    "music_bright": preset.music_bright,
                    "analog_color": preset.analog_color,
                },
            }
            for name, preset in PRESETS.items()
        }

    @router.post("/stem-rebalance")
    async def create_stem_rebalance(request: StemRebalanceRequest) -> dict:
        if request.profile not in PRESETS:
            raise HTTPException(status_code=400, detail=f"Unknown profile: {request.profile}")

        try:
            return process_rebalance_master(
                request.input_path,
                request.output_path,
                model=request.model,
                stems_dir=request.stems_dir,
                profile_name=request.profile,
                mastering_preset=request.mastering_preset,
                report_path=request.report_path,
                keep_stems=request.keep_stems,
                skip_final_master=request.skip_final_master,
                mix_mode=request.mix_mode,
                control_overrides=request.controls.enabled() if request.controls else None,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/tracks")
    async def upload_track(file: UploadFile = File(...), model: str = "mdx_extra") -> dict:
        try:
            record = track_jobs.create_track(file.file, file.filename, model=model)
            return track_jobs.to_payload(record)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/tracks/{track_id}")
    async def get_track(track_id: str) -> dict:
        try:
            return track_jobs.to_payload(track_jobs.require_track(track_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Track not found") from exc

    @router.get("/tracks/{track_id}/audio/original")
    async def get_original_audio(track_id: str) -> FileResponse:
        try:
            record = track_jobs.require_track(track_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Track not found") from exc
        return FileResponse(record.original_path, media_type="audio/wav", filename="original.wav")

    @router.get("/tracks/{track_id}/stems/{stem_name}")
    async def get_stem_audio(track_id: str, stem_name: str) -> FileResponse:
        try:
            record = track_jobs.require_track(track_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Track not found") from exc
        if stem_name not in STEM_NAMES:
            raise HTTPException(status_code=404, detail="Stem not found")
        if not record.stems_dir:
            raise HTTPException(status_code=409, detail="Track is not separated yet")

        stem_path = Path(record.stems_dir) / f"{stem_name}.wav"
        if not stem_path.exists():
            raise HTTPException(status_code=404, detail="Stem file not found")
        return FileResponse(stem_path, media_type="audio/wav", filename=f"{stem_name}.wav")

    @router.post("/tracks/{track_id}/render")
    async def render_track(track_id: str, request: RenderRequest) -> dict:
        if request.profile not in PRESETS:
            raise HTTPException(status_code=400, detail=f"Unknown profile: {request.profile}")

        try:
            record = track_jobs.require_track(track_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Track not found") from exc
        if record.status not in ("ready_to_mix", "done", "failed"):
            raise HTTPException(status_code=409, detail=f"Track is {record.status}")

        params = RenderParams(
            profile=request.profile,
            mastering_preset=request.mastering_preset,
            controls=request.controls.enabled() if request.controls else {},
            mix_mode=request.mix_mode,
            skip_final_master=request.skip_final_master,
        )
        return track_jobs.to_payload(track_jobs.render_track(track_id, params))

    @router.get("/tracks/{track_id}/download")
    async def download_track(track_id: str) -> FileResponse:
        try:
            record = track_jobs.require_track(track_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Track not found") from exc
        if not record.output_path:
            raise HTTPException(status_code=409, detail="Rendered file is not ready")
        return FileResponse(record.output_path, media_type="audio/wav", filename="master.wav")
else:  # pragma: no cover
    router = None

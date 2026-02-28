from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import (
    AssetJobCreateRequest,
    AssetJobCreateResponse,
    AssetJobStatusResponse,
    JobResultResponse,
    LegacyGenerateResponse,
)
from app.services.pipeline import PipelineService

router = APIRouter()
service = PipelineService()


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/assets/jobs/video", response_model=AssetJobCreateResponse, tags=["assets"])
def create_video_job(payload: AssetJobCreateRequest) -> AssetJobCreateResponse:
    try:
        return service.create_job(payload, mode="video")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job creation failed: {exc}") from exc


@router.post("/api/assets/jobs/storyboard", response_model=AssetJobCreateResponse, tags=["assets"])
def create_storyboard_job(payload: AssetJobCreateRequest) -> AssetJobCreateResponse:
    try:
        return service.create_job(payload, mode="image_voice_music")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job creation failed: {exc}") from exc


@router.post("/api/assets/jobs", response_model=AssetJobCreateResponse, tags=["assets"])
def create_asset_job(payload: AssetJobCreateRequest) -> AssetJobCreateResponse:
    # Default path is storyboard to avoid accidental Veo costs.
    try:
        return service.create_job(payload, mode="image_voice_music")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job creation failed: {exc}") from exc


@router.get("/api/assets/jobs/{job_id}", response_model=AssetJobStatusResponse, tags=["assets"])
def get_asset_job_status(job_id: str) -> AssetJobStatusResponse:
    try:
        return service.get_status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Status lookup failed: {exc}") from exc


@router.get("/api/assets/jobs/{job_id}/result", response_model=JobResultResponse, tags=["assets"])
def get_asset_job_result(job_id: str) -> JobResultResponse:
    try:
        return service.get_result(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Result not ready: {job_id}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Result lookup failed: {exc}") from exc


@router.post("/api/assets/generate", tags=["assets"])
def generate_assets_legacy(payload: AssetJobCreateRequest):
    try:
        status_code, body = service.wait_for_legacy(payload, mode="image_voice_music")
        if status_code == 200:
            return LegacyGenerateResponse(**body)
        if status_code == 202:
            return JSONResponse(status_code=202, content=body)
        return JSONResponse(status_code=500, content=body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Asset generation failed: {exc}") from exc

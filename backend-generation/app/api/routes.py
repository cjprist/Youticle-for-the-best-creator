from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import AssetJobCreateResponse, AssetJobStatusResponse, JobResultResponse, LegacyGenerateResponse
from app.services.pipeline import PipelineService
from app.services.payload_normalizer import normalize_asset_job_payload

router = APIRouter()
service = PipelineService()


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/assets/jobs/storyboard", response_model=AssetJobCreateResponse, tags=["assets"])
def create_storyboard_job(payload: dict) -> AssetJobCreateResponse:
    try:
        normalized = normalize_asset_job_payload(payload)
        return service.create_job(normalized, mode="storyboard")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job creation failed: {exc}") from exc


@router.post("/api/assets/jobs/storyboard-to-video", response_model=AssetJobCreateResponse, tags=["assets"])
def create_storyboard_to_video_job(payload: dict) -> AssetJobCreateResponse:
    try:
        normalized = normalize_asset_job_payload(payload)
        return service.create_job(normalized, mode="storyboard_to_video")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job creation failed: {exc}") from exc


@router.post("/api/assets/jobs", response_model=AssetJobCreateResponse, tags=["assets"])
def create_asset_job(payload: dict) -> AssetJobCreateResponse:
    try:
        normalized = normalize_asset_job_payload(payload)
        return service.create_job(normalized, mode="storyboard")
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
def generate_assets_legacy(payload: dict):
    try:
        normalized = normalize_asset_job_payload(payload)
        status_code, body = service.wait_for_legacy(normalized, mode="storyboard")
        if status_code == 200:
            return LegacyGenerateResponse(**body)
        if status_code == 202:
            return JSONResponse(status_code=202, content=body)
        return JSONResponse(status_code=500, content=body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Asset generation failed: {exc}") from exc

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    AudioGenerateRequest,
    AudioGenerateResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    ThumbnailFromScriptRequest,
    ThumbnailFromScriptResponse,
    TextGenerateRequest,
    TextGenerateResponse,
    VideoJobCreateRequest,
    VideoJobCreateResponse,
    VideoJobStatusResponse,
)
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/api/v1/generation", tags=["generation"])


@router.post("/text", response_model=TextGenerateResponse)
def generate_text(payload: TextGenerateRequest) -> TextGenerateResponse:
    try:
        service = GeminiService()
        return TextGenerateResponse(**service.generate_text(payload))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Text generation failed: {exc}") from exc


@router.post("/image", response_model=ImageGenerateResponse)
def generate_image(payload: ImageGenerateRequest) -> ImageGenerateResponse:
    try:
        service = GeminiService()
        return ImageGenerateResponse(**service.generate_image(payload))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}") from exc


@router.post("/video/jobs", response_model=VideoJobCreateResponse)
def create_video_job(payload: VideoJobCreateRequest) -> VideoJobCreateResponse:
    try:
        service = GeminiService()
        return VideoJobCreateResponse(**service.create_video_job(payload))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video job creation failed: {exc}") from exc


@router.post("/audio", response_model=AudioGenerateResponse)
def generate_audio(payload: AudioGenerateRequest) -> AudioGenerateResponse:
    try:
        service = GeminiService()
        return AudioGenerateResponse(**service.generate_audio(payload))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {exc}") from exc


@router.post("/thumbnail/script", response_model=ThumbnailFromScriptResponse)
def generate_thumbnail_from_script(
    payload: ThumbnailFromScriptRequest,
) -> ThumbnailFromScriptResponse:
    try:
        service = GeminiService()
        return ThumbnailFromScriptResponse(**service.generate_thumbnail_from_script(payload))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Thumbnail generation from script failed: {exc}"
        ) from exc


@router.get("/video/jobs/{operation_name:path}", response_model=VideoJobStatusResponse)
def get_video_job_status(
    operation_name: str,
    model: str | None = Query(default=None, description="Optional model override"),
) -> VideoJobStatusResponse:
    try:
        service = GeminiService()
        return VideoJobStatusResponse(**service.get_video_job(operation_name, model=model))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video job status lookup failed: {exc}") from exc

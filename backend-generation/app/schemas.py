from typing import Any

from pydantic import BaseModel, Field


class TextGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str | None = None


class TextGenerateResponse(BaseModel):
    text: str
    model: str


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str | None = None


class ImageGenerateResponse(BaseModel):
    model: str
    mime_types: list[str]
    images_base64: list[str]
    text: str | None = None


class VideoJobCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str | None = None
    aspect_ratio: str | None = "16:9"
    resolution: str | None = "720p"
    negative_prompt: str | None = None


class VideoJobCreateResponse(BaseModel):
    operation_name: str
    model: str
    done: bool


class VideoJobStatusResponse(BaseModel):
    operation_name: str
    done: bool
    state: str
    model: str
    video_file_uris: list[str] = []
    raw: dict[str, Any] | None = None


class AudioGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str | None = None
    voice_name: str | None = "Kore"


class AudioGenerateResponse(BaseModel):
    model: str
    mime_type: str
    audio_base64: str


class ThumbnailFromScriptRequest(BaseModel):
    title: str = Field(..., min_length=1, description="YouTube video title")
    script: str = Field(..., min_length=1, description="Video script or narration")
    visual_style: str | None = Field(
        default="bright, high-contrast, clickable YouTube thumbnail style"
    )
    language: str | None = Field(default="ko")
    model: str | None = None


class ThumbnailFromScriptResponse(BaseModel):
    model: str
    prompt_used: str
    mime_type: str
    image_base64: str

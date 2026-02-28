import base64
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import (
    AudioGenerateRequest,
    ImageGenerateRequest,
    ThumbnailFromScriptRequest,
    TextGenerateRequest,
    VideoJobCreateRequest,
)


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gcp_project_id:
            raise ValueError("GCP_PROJECT_ID is required for Vertex AI.")

        self.settings = settings
        self.vertex_client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        self.api_key_client = (
            genai.Client(api_key=settings.generation_gemini_api_key)
            if settings.generation_gemini_api_key
            else None
        )

    def generate_text(self, request: TextGenerateRequest) -> dict[str, Any]:
        model = request.model or self.settings.gcp_vertex_text_model
        response = self.vertex_client.models.generate_content(model=model, contents=request.prompt)
        return {"text": response.text or "", "model": model}

    def generate_image(self, request: ImageGenerateRequest) -> dict[str, Any]:
        model = request.model or self.settings.gcp_vertex_image_model
        response = self.vertex_client.models.generate_images(
            model=model,
            prompt=request.prompt,
            config=types.GenerateImagesConfig(number_of_images=1),
        )

        images_base64: list[str] = []
        mime_types: list[str] = []
        if getattr(response, "generated_images", None):
            for image in response.generated_images:
                image_data = getattr(image, "image", None)
                if image_data and getattr(image_data, "image_bytes", None):
                    images_base64.append(base64.b64encode(image_data.image_bytes).decode("utf-8"))
                    mime_types.append("image/png")

        return {
            "model": model,
            "mime_types": mime_types,
            "images_base64": images_base64,
            "text": None,
        }

    def create_video_job(self, request: VideoJobCreateRequest) -> dict[str, Any]:
        model = request.model or self.settings.gcp_vertex_video_model
        operation = self.vertex_client.models.generate_videos(
            model=model,
            prompt=request.prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=request.aspect_ratio,
                resolution=request.resolution,
                negative_prompt=request.negative_prompt,
            ),
        )
        return {"operation_name": operation.name, "done": bool(operation.done), "model": model}

    def get_video_job(self, operation_name: str, model: str | None = None) -> dict[str, Any]:
        selected_model = model or self.settings.gcp_vertex_video_model
        operation = self.vertex_client.operations.get(
            operation=types.GenerateVideosOperation(name=operation_name)
        )

        uris: list[str] = []
        response_payload = getattr(operation, "response", None)
        if response_payload and getattr(response_payload, "generated_videos", None):
            for generated_video in response_payload.generated_videos:
                video = getattr(generated_video, "video", None)
                if video and getattr(video, "uri", None):
                    uris.append(video.uri)

        raw = operation.model_dump() if hasattr(operation, "model_dump") else None
        return {
            "operation_name": operation.name,
            "done": bool(operation.done),
            "state": "SUCCEEDED" if operation.done else "RUNNING",
            "model": selected_model,
            "video_file_uris": uris,
            "raw": raw,
        }

    def generate_audio(self, request: AudioGenerateRequest) -> dict[str, Any]:
        model = request.model or self.settings.gcp_vertex_audio_model
        response = self.vertex_client.models.generate_content(
            model=model,
            contents=request.prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=request.voice_name or "Kore"
                        )
                    )
                ),
            ),
        )

        for candidate in response.candidates or []:
            if not candidate.content:
                continue
            for part in candidate.content.parts or []:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and inline_data.data:
                    return {
                        "model": model,
                        "mime_type": inline_data.mime_type or "audio/wav",
                        "audio_base64": base64.b64encode(inline_data.data).decode("utf-8"),
                    }

        raise ValueError("No audio data returned from model.")

    def generate_thumbnail_from_script(self, request: ThumbnailFromScriptRequest) -> dict[str, Any]:
        model = request.model or self.settings.gcp_vertex_thumbnail_model
        prompt = self._build_thumbnail_prompt(
            title=request.title,
            script=request.script,
            visual_style=request.visual_style or "",
            language=request.language or "ko",
        )

        # Prefer Gemini API key path for this feature; fallback to Vertex client.
        client = self.api_key_client or self.vertex_client

        try:
            response = client.models.generate_images(
                model=model,
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1),
            )
        except Exception:
            if client is self.api_key_client:
                response = self.vertex_client.models.generate_images(
                    model=model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(number_of_images=1),
                )
            else:
                raise

        if not getattr(response, "generated_images", None):
            raise ValueError("No image returned from model.")

        image = response.generated_images[0]
        image_data = getattr(image, "image", None)
        if not image_data or not getattr(image_data, "image_bytes", None):
            raise ValueError("Image payload is empty.")

        return {
            "model": model,
            "prompt_used": prompt,
            "mime_type": "image/png",
            "image_base64": base64.b64encode(image_data.image_bytes).decode("utf-8"),
        }

    @staticmethod
    def _build_thumbnail_prompt(title: str, script: str, visual_style: str, language: str) -> str:
        script_summary = script.strip().replace("\n", " ")
        if len(script_summary) > 500:
            script_summary = script_summary[:500] + "..."

        return (
            "Create a YouTube thumbnail image.\n"
            f"Language for text on thumbnail: {language}\n"
            f"Title to emphasize: {title}\n"
            f"Core script context: {script_summary}\n"
            f"Visual style: {visual_style}\n"
            "Requirements: one clear focal dog subject, expressive emotion, bold readable text area, "
            "high contrast, cinematic lighting, no watermark."
        )

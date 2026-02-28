from __future__ import annotations

import urllib.request
from pathlib import Path

from google import genai
from google.genai import types

from app.config import get_settings


class VertexProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gcp_project_id:
            raise ValueError("GCP_PROJECT_ID is required.")
        self.settings = settings
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )

    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        reference_images: list[Path] | None = None,
    ) -> Path:
        contents: list[object] = [prompt]
        for reference in reference_images or []:
            if not reference.exists():
                continue
            contents.append(
                types.Part.from_bytes(data=reference.read_bytes(), mime_type="image/png")
            )

        response = self.client.models.generate_content(
            model=self.settings.gcp_vertex_image_model,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=[types.Modality.IMAGE]),
        )
        image_bytes = None
        for candidate in response.candidates or []:
            if not candidate.content:
                continue
            for part in candidate.content.parts or []:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and inline_data.data:
                    image_bytes = inline_data.data
                    break
            if image_bytes:
                break

        if not image_bytes:
            raise ValueError("Gemini image payload missing.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        return output_path

    def generate_video(
        self,
        prompt: str,
        output_path: Path,
        duration_sec: int,
        image_path: Path | None = None,
    ) -> Path:
        kwargs: dict[str, object] = {
            "model": self.settings.gcp_vertex_video_model,
            "prompt": prompt,
            "config": types.GenerateVideosConfig(
                duration_seconds=duration_sec,
                aspect_ratio="16:9",
                resolution="720p",
            ),
        }
        if image_path and image_path.exists():
            try:
                kwargs["image"] = types.Image.from_file(location=str(image_path), mime_type="image/png")
            except TypeError:
                kwargs["image"] = types.Image.from_file(str(image_path))

        operation = self.client.models.generate_videos(**kwargs)
        max_polls = 45
        for _ in range(max_polls):
            operation = self.client.operations.get(operation=operation)
            if operation.done:
                break
        if not operation.done:
            raise TimeoutError("Vertex video generation timed out.")

        response_payload = getattr(operation, "response", None)
        if not response_payload or not getattr(response_payload, "generated_videos", None):
            raise ValueError("Vertex video generation returned no output.")

        video_obj = response_payload.generated_videos[0].video
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(video_obj, "save"):
            video_obj.save(str(output_path))
            return output_path

        video_uri = getattr(video_obj, "uri", None)
        if not video_uri:
            raise ValueError("Generated video URI not found.")

        urllib.request.urlretrieve(video_uri, output_path)
        return output_path

    def generate_tts_wav(self, script_text: str, output_path: Path) -> Path:
        response = self.client.models.generate_content(
            model=self.settings.gcp_vertex_audio_model,
            contents=script_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
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
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(inline_data.data)
                    return output_path
        raise ValueError("Vertex TTS returned no audio bytes.")

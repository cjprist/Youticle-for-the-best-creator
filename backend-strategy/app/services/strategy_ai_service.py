import json
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import CommentBasedStrategyRequest


class StrategyAIService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gcp_project_id:
            raise ValueError("GCP_PROJECT_ID is required for strategy backend.")

        self.settings = settings
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )

    def generate_next_video_script(self, request: CommentBasedStrategyRequest) -> dict[str, Any]:
        model = self.settings.strategy_vertex_text_model
        comments_block = "\n".join(f"- {c}" for c in request.comments)
        prompt = (
            "You are a YouTube content strategist for a dog channel.\n"
            "Assume all comments are positive feedback and feature requests.\n"
            "Return only strict JSON with keys:\n"
            "insight_summary, next_video_title, hook, cta, script.\n"
            "Write response language matching `language`.\n\n"
            f"channel_name: {request.channel_name}\n"
            f"latest_video_topic: {request.latest_video_topic}\n"
            f"tone: {request.tone or 'warm and energetic'}\n"
            f"language: {request.language or 'ko'}\n"
            "comments:\n"
            f"{comments_block}\n"
        )

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        text = response.text or ""
        data = json.loads(text)
        data["model"] = model
        return data

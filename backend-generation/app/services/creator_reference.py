from __future__ import annotations

import json
import re
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import AssetJobCreateRequest


class CreatorReferenceService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = genai.Client(
            vertexai=True,
            project=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        stripped = (text or "").strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        fenced = re.search(r"```json\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))
        block = re.search(r"(\{.*\})", stripped, flags=re.DOTALL)
        if block:
            return json.loads(block.group(1))
        return {}

    def _prompt(self, payload: AssetJobCreateRequest) -> str:
        text_blob = (
            f"제목: {payload.script.title}\n"
            f"설명: {payload.meta.description}\n"
            f"후킹: {payload.script.hook_0_15s}\n"
            f"본문1: {payload.script.body_15_150s[0].line if payload.script.body_15_150s else ''}\n"
            f"결론: {payload.rationale_block.logic.conclusion}\n"
        )
        return (
            "너는 유튜브 콘텐츠 레퍼런스 리서처다. 한국어 JSON만 출력한다.\n"
            "목표: 입력 문맥과 가장 관련 깊은 유튜버/크리에이터 1명을 추정하고,\n"
            "그 인물의 외형/분위기 참고사항을 이미지 생성용으로 요약한다.\n"
            "가능하면 검색 기반 근거를 사용한다.\n"
            "중요: 인물의 완전한 복제나 딥페이크 유도 대신, 분위기/스타일 유사도 참고 수준으로 작성.\n"
            "스키마:\n"
            "{\n"
            '  "creator_name": "string",\n'
            '  "confidence": 0.0,\n'
            '  "reference_creator_style": "string",\n'
            '  "visual_traits": ["string"],\n'
            '  "styling_notes": ["string"],\n'
            '  "search_evidence": [{"title":"string","url":"string","note":"string"}],\n'
            '  "search_used": true\n'
            "}\n"
            f"입력:\n{text_blob}"
        )

    def resolve(self, payload: AssetJobCreateRequest) -> dict[str, Any]:
        prompt = self._prompt(payload)
        config_kwargs: dict[str, Any] = {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        }
        if self.settings.creator_reference_search_enabled:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

        try:
            response = self.client.models.generate_content(
                model=self.settings.creator_reference_model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            parsed = self._extract_json(response.text or "")
            if parsed:
                return parsed
        except Exception:
            pass

        # Fallback without search tool.
        response = self.client.models.generate_content(
            model=self.settings.creator_reference_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        parsed = self._extract_json(response.text or "")
        return parsed or {
            "creator_name": "",
            "confidence": 0.0,
            "reference_creator_style": "",
            "visual_traits": [],
            "styling_notes": [],
            "search_evidence": [],
            "search_used": False,
        }

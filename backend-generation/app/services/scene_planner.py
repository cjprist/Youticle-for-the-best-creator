from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import AssetJobCreateRequest


@dataclass(frozen=True)
class PlannedScene:
    scene_no: int
    source_span: str
    intent: str
    subject: str
    action: str
    location_context: str
    left_props: list[str]
    camera_shot: str
    camera_angle: str
    foreground_midground_background: str


@dataclass(frozen=True)
class ScenePlanResult:
    character_bible: dict[str, Any]
    consistency_rules: list[str]
    thumbnail_plan: dict[str, Any]
    scenes: list[PlannedScene]


class ScenePlannerService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = genai.Client(
            vertexai=True,
            project=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
        )

    @staticmethod
    def _scene_sources(payload: AssetJobCreateRequest) -> list[str]:
        return ["hook", "body_0", "body_1", "body_2_or_conclusion", "closing+conclusion"]

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        stripped = (text or "").strip()
        if not stripped:
            raise ValueError("Scene planner returned empty text.")
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
        raise ValueError("Scene planner JSON parse failed.")

    def _build_prompt(
        self, payload: AssetJobCreateRequest, creator_reference: dict[str, Any] | None = None
    ) -> str:
        body_lines = [{"t": b.t, "line": b.line} for b in payload.script.body_15_150s]
        planner_input = {
            "meta": {
                "title": payload.script.title,
                "language": payload.meta.language,
                "target_audience": payload.meta.target_audience,
                "description": payload.meta.description,
            },
            "rationale": {
                "observations": payload.rationale_block.logic.observations,
                "inference": payload.rationale_block.logic.inference,
                "conclusion": payload.rationale_block.logic.conclusion,
            },
            "script": {
                "hook_0_15s": payload.script.hook_0_15s,
                "body_15_150s": body_lines,
                "closing_150_180s": payload.script.closing_150_180s,
            },
            "assets": {"on_screen_bullets": payload.assets.on_screen_bullets},
            "scene_sources": self._scene_sources(payload),
            "creator_reference": creator_reference or {},
        }
        return (
            "너는 영상 스토리보드 씬 플래너다. 반드시 한국어로 응답한다.\n"
            "설명문 없이 JSON 객체만 출력한다.\n"
            "아래 입력 대본을 바탕으로 5개 장면을 동적으로 설계하라.\n"
            "중요 규칙:\n"
            "1) scene_plan은 정확히 5개.\n"
            "2) source_span은 순서대로 hook, body_0, body_1, body_2_or_conclusion, closing+conclusion.\n"
            "3) 모든 장면은 동일 인물 1명을 유지할 수 있도록 character_bible을 구체화.\n"
            "4) 프레임은 상황 재연 중심(주체/행동/배경/소품/카메라)으로 작성.\n"
            "5) left_props는 실사형 사물 상징 2~3개.\n"
            "6) 캐릭터는 실사풍으로 설계하고, 대본 주제와 관련된 유튜버 인상/분위기를 반영.\n"
            "7) 텍스트는 소량 허용: 장면당 한국어 1~3단어, 최대 12자 수준. 영문 장문 금지.\n"
            "JSON 스키마:\n"
            "{\n"
            '  "character_bible": {\n'
            '    "identity": "...", "age_range": "...", "face_shape": "...", "hair_style": "...",\n'
            '    "outfit": "...", "outfit_colors": ["..."], "expression_range": "...",\n'
            '    "reference_creator_style": "...",\n'
            '    "forbidden_changes": ["..."]\n'
            "  },\n"
            '  "consistency_rules": ["..."],\n'
            '  "thumbnail_plan": {\n'
            '    "intent": "...", "subject": "...", "action": "...", "left_props": ["..."],\n'
            '    "camera_shot": "...", "camera_angle": "...", "tension_point": "..."\n'
            "  },\n"
            '  "scene_plan": [\n'
            "    {\n"
            '      "scene_no": 1, "source_span": "hook", "intent": "...", "subject": "...",\n'
            '      "action": "...", "location_context": "...", "left_props": ["..."],\n'
            '      "camera_shot": "...", "camera_angle": "...",\n'
            '      "foreground_midground_background": "..."\n'
            "    }\n"
            "  ]\n"
            "}\n"
            f"입력:\n{json.dumps(planner_input, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _validate(result: dict[str, Any]) -> ScenePlanResult:
        character_bible = result.get("character_bible", {})
        consistency_rules = result.get("consistency_rules", [])
        thumbnail_plan = result.get("thumbnail_plan", {})
        scene_plan = result.get("scene_plan", [])

        if not isinstance(character_bible, dict):
            raise ValueError("character_bible missing")
        if not isinstance(consistency_rules, list):
            raise ValueError("consistency_rules missing")
        if not isinstance(thumbnail_plan, dict):
            raise ValueError("thumbnail_plan missing")
        if not isinstance(scene_plan, list) or len(scene_plan) != 5:
            raise ValueError("scene_plan must have exactly 5 scenes")

        scenes: list[PlannedScene] = []
        for item in scene_plan:
            if not isinstance(item, dict):
                raise ValueError("scene item must be object")
            scenes.append(
                PlannedScene(
                    scene_no=int(item.get("scene_no", len(scenes) + 1)),
                    source_span=str(item.get("source_span", "")),
                    intent=str(item.get("intent", "")),
                    subject=str(item.get("subject", "")),
                    action=str(item.get("action", "")),
                    location_context=str(item.get("location_context", "")),
                    left_props=[str(x) for x in (item.get("left_props") or [])][:3],
                    camera_shot=str(item.get("camera_shot", "")),
                    camera_angle=str(item.get("camera_angle", "")),
                    foreground_midground_background=str(
                        item.get("foreground_midground_background", "")
                    ),
                )
            )

        return ScenePlanResult(
            character_bible=character_bible,
            consistency_rules=[str(x) for x in consistency_rules],
            thumbnail_plan=thumbnail_plan,
            scenes=scenes,
        )

    def plan(
        self, payload: AssetJobCreateRequest, creator_reference: dict[str, Any] | None = None
    ) -> ScenePlanResult:
        prompt = self._build_prompt(payload, creator_reference=creator_reference)
        last_error: Exception | None = None
        for attempt in range(self.settings.max_scene_plan_attempts):
            temperature = 0.2 if attempt > 0 else 0.5
            try:
                response = self.client.models.generate_content(
                    model=self.settings.scene_planner_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                    ),
                )
                text = response.text or ""
                parsed = self._extract_json(text)
                return self._validate(parsed)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Scene planner failed: {last_error}") from last_error

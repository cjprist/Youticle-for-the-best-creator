import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas import (
    CommentBasedStrategyRequest,
    ScriptOutputRequest,
    SignalOutputRequest,
)

SIGNAL_OUTPUT_PROMPT = """You are an analyst who extracts practical audience demand signals from YouTube comments.

Task:
Given a JSON input of videos and comments, produce exactly one JSON object that matches SignalOutput v2 schema.

Output language:
- Korean (ko) for all natural-language fields.

Hard constraints:
1) Return ONLY valid JSON. No markdown, no explanation.
2) Schema strictness:
   - All required top-level keys must exist: meta, signals, quality_checks.
   - Each signal must include: signal_id, title, category, core_question, demand, evidence, causal_model, content_plan, actionables, safety, confidence.
3) Evidence quality:
   - Exclude meme / thumbnail_meta / pure_praise from supporting evidence.
   - Allowed only in evidence.excluded_examples with reason.
4) Signal quality:
   - Each signal must have 2~4 supporting_comments.
   - At least 1 supporting comment per signal must be high-like (top tier within its video).
   - Causal chain must be explicit: observations -> inference_steps -> root_cause_hypothesis.
5) Safety:
   - Finance: no buy/sell recommendations, no target price.
   - Politics: no agitation/partisan persuasion; use conditions/costs/scenarios framing.
6) Dedupe:
   - Merge semantically similar comments/signals; avoid near-duplicate signals.
7) Perspective lock (important):
   - Write signals for the input channel owner/operator perspective.
   - core_question, demand, content_plan, actionables must be directly executable by "our channel".
   - Prefer wording like "우리 채널", "다음 영상에서 우리가".
   - Do NOT output third-person consulting tone about another creator/brand/government as primary actor.
   - Avoid recommendations that require external institutions as the main executor.

Scoring guidance (internal):
- evidence_strength: 0~1 (like_count strength + clarity + representativeness)
- recurrence_score: 0~1 (theme repetition across comments/videos)
- confidence.score: 0~1 based on evidence quality + recurrence + counterpoint handling

Filtering policy:
- meme examples: "ㅋㅋ", "개추", "썸네일 뭐야", one-liner joke/reaction
- thumbnail_meta: comments only about thumbnail/title bait/prompt
- pure_praise: "잘 봤어요", "감사합니다", "유익"
- low_info: little to no actionable meaning

Selection method:
- Group comments by semantic theme across videos.
- Prioritize themes with high likes and recurrence.
- For each signal, include representative + (optional) counterpoint evidence.

Validation rules (must pass before final output):
- Valid JSON parse.
- Type correctness by schema.
- signals_count >= 1
- each_signal_has_causal_model = true
- each_signal_has_actionables = true
- meme_excluded = true
- If any rule fails, regenerate once internally and output corrected JSON only.
"""

SCRIPT_OUTPUT_PROMPT = """You are a scriptwriter who turns one audience-demand signal into a 3-minute YouTube script.

Input:
- One signal object from SignalOutput v2 (signal_id = S#).

Task:
Produce exactly one JSON object that matches ScriptOutput v2 schema.

Output language:
- Korean (ko) for all natural-language fields.

Hard constraints:
1) Return ONLY valid JSON. No markdown, no explanation.
2) Must include rationale_block with explicit causality:
   - observations -> inference -> conclusion
   - grounded in signal.evidence + signal.causal_model only
3) Exclude memes from core evidence.
   - If present in source context, mention only in rationale_block.what_we_excluded.
4) Safety:
   - Finance: no buy/sell recommendation, no price target, no guaranteed outcome wording.
   - Politics: no agitation; conditions/costs/scenarios only.
5) Length control:
   - Target 180 seconds spoken Korean.
   - Keep sentences short and speakable.
   - body_15_150s must have exactly 4 timed blocks.
6) Perspective lock (important):
   - Write from the channel owner's point of view (first-person creator voice).
   - Treat the input signal as "our channel audience demand", not as another creator's case.
   - Prefer wording like "우리 채널", "이번 영상에서 우리가", "우리 시청자".
   - Do NOT frame the script as third-person commentary about other creators.
   - CTA must ask what this channel should do next, for this channel's next video.

Structure rules:
- hook_0_15s: problem framing + promise
- body_15_150s:
  - explain framework clearly
  - include 1~2 concrete examples
  - include practical checklist/table-compatible points
- closing_150_180s: recap + specific CTA question
- assets:
  - on_screen_bullets: concise, non-redundant
  - simple_chart_or_table: immediately displayable
  - disclaimer: neutral and safety-compliant

Style:
- informative, creator-friendly, high clarity, low jargon.
- Avoid exaggeration and absolute claims.
- owner-operator execution tone: concrete and actionable for immediate next upload.

Validation rules (must pass before final output):
- Valid JSON parse.
- Required keys exist: meta, rationale_block, script, assets.
- source_signal_id matches input signal_id.
- body blocks = 4 with valid time ranges.
- CTA is specific and comment-friendly.
- If any rule fails, regenerate once internally and output corrected JSON only.
"""

logger = logging.getLogger("uvicorn.error")


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

    def generate_signal_output_v2(self, request: SignalOutputRequest) -> dict[str, Any]:
        model = self.settings.strategy_vertex_text_model
        payload = request.model_dump(mode="json")
        prompt = (
            f"{SIGNAL_OUTPUT_PROMPT}\n\n"
            "Input JSON:\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        logger.info(
            "llm:signals request model=%s videos=%s prompt_chars=%s",
            model,
            len(payload.get("videos", [])),
            len(prompt),
        )
        logger.info("llm:signals prompt_preview=%s", prompt[:1800])

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        text = response.text or ""
        logger.info("llm:signals response_chars=%s", len(text))
        logger.info("llm:signals response_preview=%s", text[:3000])
        data = json.loads(text)
        logger.info("llm:signals response_keys=%s", list(data.keys()))
        data["model"] = model
        return data

    def generate_script_output_v2(self, request: ScriptOutputRequest) -> dict[str, Any]:
        model = self.settings.strategy_vertex_text_model
        payload = request.model_dump(mode="json")
        prompt = (
            f"{SCRIPT_OUTPUT_PROMPT}\n\n"
            "Input JSON:\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        logger.info(
            "llm:script request model=%s signal_id=%s prompt_chars=%s",
            model,
            payload.get("signal_id"),
            len(prompt),
        )
        logger.info("llm:script prompt_preview=%s", prompt[:1800])

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5,
            ),
        )
        text = response.text or ""
        logger.info("llm:script response_chars=%s", len(text))
        logger.info("llm:script response_preview=%s", text[:3000])
        data = json.loads(text)
        logger.info("llm:script response_keys=%s", list(data.keys()))
        data["model"] = model
        return data

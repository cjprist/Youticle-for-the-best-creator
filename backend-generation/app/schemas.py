from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JobOptions(BaseModel):
    max_video_seconds: int = Field(default=5, ge=3, le=5)
    fallback_mode: Literal["storyboard"] = "storyboard"
    quality_mode: Literal["balanced", "high"] = "balanced"


class MetaData(BaseModel):
    source_signal_id: str
    target_length_sec: int = Field(default=180, ge=30, le=600)
    language: str = "ko"
    style: str = "informative"
    title: str = ""
    description: str = ""
    target_audience: str = ""


class EvidenceItem(BaseModel):
    quote: str
    like_count: int | None = None
    video_id: str | None = None


class LogicBlock(BaseModel):
    observations: list[str] = []
    inference: list[str] = []
    conclusion: str = ""


class ExcludedItem(BaseModel):
    example: str
    reason: str


class RationaleBlock(BaseModel):
    title: str = ""
    evidence_summary: list[EvidenceItem] = []
    logic: LogicBlock = LogicBlock()
    what_we_excluded: list[ExcludedItem] = []


class BodyLine(BaseModel):
    t: str
    line: str


class CtaBlock(BaseModel):
    type: str = "comment_prompt"
    line: str = ""


class ScriptBlock(BaseModel):
    title: str
    hook_0_15s: str
    body_15_150s: list[BodyLine]
    closing_150_180s: str
    cta: CtaBlock = CtaBlock()


class ChartItem(BaseModel):
    label: str
    value: str


class AssetsBlock(BaseModel):
    on_screen_bullets: list[str] = []
    simple_chart_or_table: list[ChartItem] = []
    disclaimer: str = ""


class AssetJobCreateRequest(BaseModel):
    meta: MetaData
    rationale_block: RationaleBlock
    script: ScriptBlock
    assets: AssetsBlock
    options: JobOptions = JobOptions()


class AssetJobCreateResponse(BaseModel):
    job_id: str
    status: str
    status_path: str
    result_path: str
    pipeline_mode: Literal["storyboard", "storyboard_to_video"]


class AssetJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    stage: str
    progress: int
    pipeline_mode: Literal["storyboard", "storyboard_to_video", "unknown"] = "unknown"
    output_mode: Literal["storyboard", "storyboard_to_video", "unknown"] = "unknown"
    video_path: str | None = None
    alt_video_path: str | None = None
    result_path: str
    error_message: str | None = None


class LegacyGenerateResponse(BaseModel):
    request_id: str
    thumbnail_path: str
    video_path: str
    result_path: str


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    pipeline_mode: str
    output_mode: str
    quality_scores: dict[str, float]
    files: dict[str, str]
    fallback_reason: str | None = None
    provider_trace: dict[str, int | bool | str | list[str]] = {}
    prompt_version: str = ""
    frame_count: int = 0
    style_bible_applied: bool = False
    script_grounding_applied: bool = False
    scene_sources: list[str] = []
    storyboard_scene_plan: list[dict[str, str | list[str]]] = []
    image_model: str = ""
    scene_planner_model: str = ""
    character_bible: dict[str, str | list[str]] = {}
    scene_plan_path: str = ""
    character_anchor_path: str = ""
    text_guard_enabled: bool = False
    text_guard_summary: dict[str, int | bool | str | list[str]] = {}
    veo_trace: dict[str, str | int | bool] = {}
    partial_result: bool = False
    error_message: str | None = None

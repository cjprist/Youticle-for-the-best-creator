from pydantic import BaseModel, Field


class StrategyRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Content topic")
    target_audience: str = Field(..., min_length=1, description="Target audience")
    objective: str = Field(..., min_length=1, description="Channel objective")


class StrategyItem(BaseModel):
    step: int
    title: str
    detail: str
    suggested_output_type: str


class StrategyResponse(BaseModel):
    summary: str
    strategy: list[StrategyItem]


class CommentBasedStrategyRequest(BaseModel):
    channel_name: str = Field(..., min_length=1)
    latest_video_topic: str = Field(..., min_length=1)
    comments: list[str] = Field(..., min_length=1, description="Collected comments")
    tone: str | None = Field(default="warm and energetic")
    language: str | None = Field(default="ko")


class CommentBasedStrategyResponse(BaseModel):
    insight_summary: str
    next_video_title: str
    hook: str
    cta: str
    script: str
    model: str

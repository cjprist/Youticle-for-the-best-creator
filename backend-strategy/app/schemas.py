from datetime import datetime
from typing import Any

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


class YouTubeCommentsRequest(BaseModel):
    channel_handle: str = Field(
        ..., min_length=1, description="YouTube handle (e.g. @youtubers)"
    )
    max_videos: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of latest videos to fetch comments from",
    )
    max_comments_per_video: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of comments to collect per video",
    )


class YouTubeComment(BaseModel):
    comment_id: str
    parent_comment_id: str | None = None
    author: str | None = None
    text: str
    like_count: int
    published_at: datetime | None = None


class VideoComments(BaseModel):
    video_id: str
    video_title: str | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    comment_count: int
    comments: list[YouTubeComment]


class YouTubeCommentsResponse(BaseModel):
    channel_handle: str
    channel_id: str
    channel_name: str | None = None
    channel_thumbnail_url: str | None = None
    subscriber_count: int | None = None
    video_count: int
    videos: list[VideoComments]


class SignalComment(BaseModel):
    author: str | None = None
    text: str
    published_at: datetime | None = None
    like_count: int = 0


class SignalVideo(BaseModel):
    video_id: str
    title: str | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    comments: list[SignalComment] = Field(default_factory=list)
    comment_error: str | None = None


class SignalFilters(BaseModel):
    min_like: int = 0
    topk_per_video: int = 50
    exclude_meme: bool = True
    exclude_thumbnail_meta: bool = True
    exclude_pure_praise: bool = True
    dedupe: str = "semantic"


class SignalOutputRequest(BaseModel):
    videos: list[SignalVideo] = Field(..., min_length=1)
    language: str = "ko"
    filters: SignalFilters = Field(default_factory=SignalFilters)


class SignalOutputResponse(BaseModel):
    meta: dict[str, Any]
    signals: list[dict[str, Any]]
    quality_checks: dict[str, Any]
    model: str


class ScriptOutputRequest(BaseModel):
    signal: dict[str, Any]
    signal_id: str
    language: str = "ko"
    target_length_sec: int = 180
    style: str = "informative"


class ScriptOutputResponse(BaseModel):
    meta: dict[str, Any]
    rationale_block: dict[str, Any]
    script: dict[str, Any]
    assets: dict[str, Any]
    model: str


class ChannelPipelineRequest(BaseModel):
    channel_handle: str = Field(
        ..., min_length=1, description="YouTube handle (e.g. @youtubers)"
    )
    max_videos: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of latest videos to fetch comments from",
    )
    max_comments_per_video: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of comments to collect per video",
    )
    language: str = "ko"
    target_length_sec: int = 180
    style: str = "informative"
    signal_id: str | None = None


class ChannelPipelineResponse(BaseModel):
    channel_handle: str
    channel_id: str
    video_count: int
    signal_output: dict[str, Any]
    selected_signal_id: str
    script_output: dict[str, Any]

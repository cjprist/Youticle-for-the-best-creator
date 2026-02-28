import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import (
    ChannelPipelineRequest,
    ChannelPipelineResponse,
    CommentBasedStrategyRequest,
    CommentBasedStrategyResponse,
    ScriptOutputRequest,
    ScriptOutputResponse,
    SignalOutputRequest,
    SignalOutputResponse,
    StrategyItem,
    StrategyRequest,
    StrategyResponse,
    YouTubeCommentsRequest,
    YouTubeCommentsResponse,
)
from app.services.strategy_ai_service import StrategyAIService
from app.services.youtube_service import YouTubeCommentService, YouTubeDataAPIError

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])
# Reuse uvicorn logger so route-level debug logs always appear in docker logs.
logger = logging.getLogger("uvicorn.error")


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _build_comment_video_lookup(videos: list[Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for video in videos:
        video_id = getattr(video, "video_id", None) if not isinstance(video, dict) else video.get("video_id")
        title = getattr(video, "title", None) if not isinstance(video, dict) else video.get("title")
        thumbnail_url = (
            getattr(video, "thumbnail_url", None)
            if not isinstance(video, dict)
            else video.get("thumbnail_url")
        )
        published_at = (
            getattr(video, "published_at", None)
            if not isinstance(video, dict)
            else video.get("published_at")
        )
        comments = getattr(video, "comments", []) if not isinstance(video, dict) else video.get("comments", [])

        for comment in comments or []:
            text = getattr(comment, "text", None) if not isinstance(comment, dict) else comment.get("text")
            if not text:
                continue
            normalized = _normalize_text(text)
            if not normalized or normalized in lookup:
                continue
            lookup[normalized] = {
                "video_id": video_id,
                "video_title": title,
                "thumbnail_url": thumbnail_url,
                "video_published_at": published_at.isoformat() if hasattr(published_at, "isoformat") else published_at,
            }
    return lookup


def _build_video_id_lookup(videos: list[Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for video in videos:
        video_id = getattr(video, "video_id", None) if not isinstance(video, dict) else video.get("video_id")
        if not video_id:
            continue
        title = getattr(video, "title", None) if not isinstance(video, dict) else video.get("title")
        thumbnail_url = (
            getattr(video, "thumbnail_url", None)
            if not isinstance(video, dict)
            else video.get("thumbnail_url")
        )
        published_at = (
            getattr(video, "published_at", None)
            if not isinstance(video, dict)
            else video.get("published_at")
        )
        lookup[str(video_id)] = {
            "video_id": video_id,
            "video_title": title,
            "thumbnail_url": thumbnail_url,
            "video_published_at": published_at.isoformat() if hasattr(published_at, "isoformat") else published_at,
        }
    return lookup


def _enrich_signals_with_video_context(
    signal_output: dict[str, Any],
    videos: list[Any],
) -> dict[str, Any]:
    signals = signal_output.get("signals", [])
    if not isinstance(signals, list) or not signals:
        return signal_output

    comment_lookup = _build_comment_video_lookup(videos)
    video_id_lookup = _build_video_id_lookup(videos)
    for signal in signals:
        if not isinstance(signal, dict):
            continue

        evidence = signal.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
            signal["evidence"] = evidence

        supporting_comments = evidence.get("supporting_comments")
        if not isinstance(supporting_comments, list):
            supporting_comments = []
            evidence["supporting_comments"] = supporting_comments

        source_videos_map: dict[str, dict[str, Any]] = {}
        for comment in supporting_comments:
            if not isinstance(comment, dict):
                continue
            text = comment.get("text") or comment.get("comment_text")
            matched = None
            if isinstance(text, str) and text.strip():
                matched = comment_lookup.get(_normalize_text(text))
            if not matched and comment.get("video_id"):
                matched = video_id_lookup.get(str(comment.get("video_id")))

            if matched:
                comment.setdefault("video_id", matched.get("video_id"))
                comment.setdefault("video_title", matched.get("video_title"))
                comment.setdefault("thumbnail_url", matched.get("thumbnail_url"))
                comment.setdefault("video_published_at", matched.get("video_published_at"))

            video_id = comment.get("video_id")
            if not video_id:
                continue

            source_videos_map[str(video_id)] = {
                "video_id": video_id,
                "video_title": comment.get("video_title"),
                "thumbnail_url": comment.get("thumbnail_url"),
                "video_published_at": comment.get("video_published_at"),
            }

        signal["source_videos"] = list(source_videos_map.values())

    return signal_output


@router.post("/plan", response_model=StrategyResponse)
def build_strategy(payload: StrategyRequest) -> StrategyResponse:
    items = [
        StrategyItem(
            step=1,
            title="Audience Insight",
            detail=f"Map 3 core needs for '{payload.target_audience}'.",
            suggested_output_type="text",
        ),
        StrategyItem(
            step=2,
            title="Content Hook",
            detail=f"Create 5 clickable hooks based on topic '{payload.topic}'.",
            suggested_output_type="text",
        ),
        StrategyItem(
            step=3,
            title="Visual Direction",
            detail="Define image/video concept for high-click thumbnail and short.",
            suggested_output_type="image_or_video_prompt",
        ),
    ]
    return StrategyResponse(
        summary=f"Initial strategy draft for objective '{payload.objective}'.",
        strategy=items,
    )


@router.post("/next-video-script", response_model=CommentBasedStrategyResponse)
def build_next_video_script(payload: CommentBasedStrategyRequest) -> CommentBasedStrategyResponse:
    try:
        service = StrategyAIService()
        result = service.generate_next_video_script(payload)
        return CommentBasedStrategyResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Strategy generation failed: {exc}") from exc


@router.post("/signals/from-comments", response_model=SignalOutputResponse)
def build_signal_output(payload: SignalOutputRequest) -> SignalOutputResponse:
    request_id = str(uuid.uuid4())[:8]
    started_at = time.perf_counter()
    logger.info(
        "[%s] signals/from-comments:start videos=%s language=%s",
        request_id,
        len(payload.videos),
        payload.language,
    )
    try:
        service = StrategyAIService()
        result = service.generate_signal_output_v2(payload)
        result = _enrich_signals_with_video_context(result, payload.videos)
        elapsed = time.perf_counter() - started_at
        logger.info(
            "[%s] signals/from-comments:done signals=%s elapsed=%.2fs",
            request_id,
            len(result.get("signals", [])),
            elapsed,
        )
        return SignalOutputResponse(**result)
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        logger.exception(
            "[%s] signals/from-comments:error elapsed=%.2fs detail=%s",
            request_id,
            elapsed,
            exc,
        )
        raise HTTPException(status_code=500, detail=f"Signal generation failed: {exc}") from exc


@router.post("/scripts/from-signal", response_model=ScriptOutputResponse)
def build_script_output(payload: ScriptOutputRequest) -> ScriptOutputResponse:
    request_id = str(uuid.uuid4())[:8]
    started_at = time.perf_counter()
    logger.info(
        "[%s] scripts/from-signal:start signal_id=%s target_length=%s style=%s",
        request_id,
        payload.signal_id,
        payload.target_length_sec,
        payload.style,
    )
    try:
        service = StrategyAIService()
        result = service.generate_script_output_v2(payload)
        elapsed = time.perf_counter() - started_at
        logger.info(
            "[%s] scripts/from-signal:done has_script=%s elapsed=%.2fs",
            request_id,
            bool(result.get("script")),
            elapsed,
        )
        return ScriptOutputResponse(**result)
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        logger.exception(
            "[%s] scripts/from-signal:error elapsed=%.2fs detail=%s",
            request_id,
            elapsed,
            exc,
        )
        raise HTTPException(status_code=500, detail=f"Script generation failed: {exc}") from exc


@router.post("/pipeline/from-handle", response_model=ChannelPipelineResponse)
def build_pipeline_from_handle(payload: ChannelPipelineRequest) -> ChannelPipelineResponse:
    request_id = str(uuid.uuid4())[:8]
    started_at = time.perf_counter()
    logger.info(
        "[%s] pipeline:start handle=%s max_videos=%s max_comments_per_video=%s comment_order=%s language=%s style=%s target_length=%s",
        request_id,
        payload.channel_handle,
        payload.max_videos,
        payload.max_comments_per_video,
        payload.comment_order,
        payload.language,
        payload.style,
        payload.target_length_sec,
    )
    try:
        comment_service = YouTubeCommentService()
        strategy_service = StrategyAIService()

        step_started_at = time.perf_counter()
        comments_response = comment_service.fetch_channel_comments(
            channel_handle=payload.channel_handle,
            max_videos=payload.max_videos,
            max_comments_per_video=payload.max_comments_per_video,
            comment_order=payload.comment_order,
        )
        logger.info(
            "[%s] pipeline:comments_collected videos=%s elapsed=%.2fs",
            request_id,
            comments_response.get("video_count"),
            time.perf_counter() - step_started_at,
        )

        step_started_at = time.perf_counter()
        signal_request = SignalOutputRequest(
            videos=[
                {
                    "video_id": v["video_id"],
                    "title": v.get("video_title"),
                    "thumbnail_url": v.get("thumbnail_url"),
                    "published_at": v.get("published_at"),
                    "comments": [
                        {
                            "author": c.get("author"),
                            "text": c["text"],
                            "published_at": c.get("published_at"),
                            "like_count": c.get("like_count", 0),
                        }
                        for c in v.get("comments", [])
                    ],
                    "comment_error": None,
                }
                for v in comments_response.get("videos", [])
            ],
            language=payload.language,
        )
        signal_output = strategy_service.generate_signal_output_v2(signal_request)
        signal_output = _enrich_signals_with_video_context(signal_output, signal_request.videos)
        logger.info(
            "[%s] pipeline:signals_generated signals=%s elapsed=%.2fs",
            request_id,
            len(signal_output.get("signals", [])),
            time.perf_counter() - step_started_at,
        )
        signals = signal_output.get("signals", [])
        if not signals:
            raise HTTPException(status_code=422, detail="No signals generated from comments.")

        selected_signal_id = payload.signal_id or signals[0].get("signal_id")
        selected_signal = next(
            (s for s in signals if s.get("signal_id") == selected_signal_id),
            None,
        )
        if not selected_signal:
            raise HTTPException(
                status_code=422,
                detail=f"Requested signal_id '{payload.signal_id}' not found.",
            )

        step_started_at = time.perf_counter()
        script_request = ScriptOutputRequest(
            signal=selected_signal,
            signal_id=selected_signal_id,
            language=payload.language,
            target_length_sec=payload.target_length_sec,
            style=payload.style,
        )
        script_output = strategy_service.generate_script_output_v2(script_request)
        logger.info(
            "[%s] pipeline:script_generated signal_id=%s elapsed=%.2fs",
            request_id,
            selected_signal_id,
            time.perf_counter() - step_started_at,
        )

        total_elapsed = time.perf_counter() - started_at
        logger.info(
            "[%s] pipeline:done handle=%s videos=%s signals=%s total_elapsed=%.2fs",
            request_id,
            comments_response.get("channel_handle"),
            comments_response.get("video_count"),
            len(signals),
            total_elapsed,
        )

        return ChannelPipelineResponse(
            channel_handle=comments_response["channel_handle"],
            channel_id=comments_response["channel_id"],
            video_count=comments_response["video_count"],
            signal_output=signal_output,
            selected_signal_id=selected_signal_id,
            script_output=script_output,
        )
    except HTTPException:
        logger.exception("[%s] pipeline:http_error", request_id)
        raise
    except (YouTubeDataAPIError, ValueError) as exc:
        logger.exception(
            "[%s] pipeline:bad_request elapsed=%.2fs detail=%s",
            request_id,
            time.perf_counter() - started_at,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "[%s] pipeline:error elapsed=%.2fs detail=%s",
            request_id,
            time.perf_counter() - started_at,
            exc,
        )
        raise HTTPException(status_code=500, detail=f"Pipeline generation failed: {exc}") from exc


@router.post("/youtube/comments", response_model=YouTubeCommentsResponse)
def collect_youtube_comments(payload: YouTubeCommentsRequest) -> YouTubeCommentsResponse:
    request_id = str(uuid.uuid4())[:8]
    started_at = time.perf_counter()
    logger.info(
        "[%s] youtube/comments:start handle=%s max_videos=%s max_comments_per_video=%s comment_order=%s",
        request_id,
        payload.channel_handle,
        payload.max_videos,
        payload.max_comments_per_video,
        payload.comment_order,
    )
    try:
        service = YouTubeCommentService()
        response = service.fetch_channel_comments(
            channel_handle=payload.channel_handle,
            max_videos=payload.max_videos,
            max_comments_per_video=payload.max_comments_per_video,
            comment_order=payload.comment_order,
        )
        logger.info(
            "[%s] youtube/comments:done videos=%s elapsed=%.2fs",
            request_id,
            response.get("video_count"),
            time.perf_counter() - started_at,
        )
        return YouTubeCommentsResponse(**response)
    except (YouTubeDataAPIError, ValueError) as exc:
        logger.exception(
            "[%s] youtube/comments:bad_request elapsed=%.2fs detail=%s",
            request_id,
            time.perf_counter() - started_at,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception(
            "[%s] youtube/comments:error elapsed=%.2fs detail=%s",
            request_id,
            time.perf_counter() - started_at,
            exc,
        )
        raise HTTPException(status_code=500, detail=f"YouTube comment collection failed: {exc}") from exc

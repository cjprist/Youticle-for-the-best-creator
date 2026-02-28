from fastapi import APIRouter, HTTPException

from app.schemas import (
    CommentBasedStrategyRequest,
    CommentBasedStrategyResponse,
    StrategyItem,
    StrategyRequest,
    StrategyResponse,
)
from app.services.strategy_ai_service import StrategyAIService

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


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

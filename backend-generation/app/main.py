from fastapi import FastAPI

from app.config import get_settings
from app.routers.gemini import router as gemini_router
from app.routers.health import router as health_router

settings = get_settings()

app = FastAPI(
    title=settings.gen_app_name,
    debug=settings.gen_app_debug,
    version="0.1.0",
    description="Generation backend for Vertex AI text/image/video/audio",
)

app.include_router(health_router)
app.include_router(gemini_router)

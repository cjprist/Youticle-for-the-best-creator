from fastapi import FastAPI

from app.api.routes import router as api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.gen_app_name,
    debug=settings.gen_app_debug,
    version="0.1.0",
    description="Script-to-thumbnail/teaser pipeline backend",
)

app.include_router(api_router)

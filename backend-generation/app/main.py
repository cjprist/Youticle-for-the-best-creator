from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.gen_app_name,
    debug=settings.gen_app_debug,
    version="0.1.0",
    description="Script-to-thumbnail/teaser pipeline backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

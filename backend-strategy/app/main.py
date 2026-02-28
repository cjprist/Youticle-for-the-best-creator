from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.health import router as health_router
from app.routers.strategy import router as strategy_router

settings = get_settings()

app = FastAPI(
    title=settings.strategy_app_name,
    debug=settings.strategy_app_debug,
    version="0.1.0",
    description="Strategy planning backend (teammate service)",
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

app.include_router(health_router)
app.include_router(strategy_router)

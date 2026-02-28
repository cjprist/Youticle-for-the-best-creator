from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gen_app_name: str = "Youticle Generation Backend"
    app_env: str = "development"
    gen_app_debug: bool = True

    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    generated_dir: str = "/workspace/frontend/public/generated"
    gcp_vertex_image_model: str = "imagen-4.0-generate-001"
    gcp_vertex_video_model: str = "veo-3.1-generate-preview"
    gcp_vertex_audio_model: str = "gemini-2.5-flash-preview-tts"
    max_worker_jobs: int = 2
    default_max_video_seconds: int = 5
    video_quality_threshold: float = 0.55
    max_video_attempts: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()

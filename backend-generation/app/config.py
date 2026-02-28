from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gen_app_name: str = "Youticle Generation Backend"
    app_env: str = "development"
    gen_app_debug: bool = True

    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    generation_gemini_api_key: str = ""
    gcp_vertex_text_model: str = "gemini-2.5-flash"
    gcp_vertex_image_model: str = "imagen-4.0-generate-001"
    gcp_vertex_thumbnail_model: str = "imagen-4.0-generate-001"
    gcp_vertex_video_model: str = "veo-3.1-generate-preview"
    gcp_vertex_audio_model: str = "gemini-2.5-flash-preview-tts"


@lru_cache
def get_settings() -> Settings:
    return Settings()

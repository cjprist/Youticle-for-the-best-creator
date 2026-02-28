from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    strategy_app_name: str = "Youticle Strategy Backend"
    strategy_app_debug: bool = True
    app_env: str = "development"
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    strategy_vertex_text_model: str = "gemini-2.5-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()

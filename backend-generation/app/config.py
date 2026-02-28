from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gen_app_name: str = "Youticle Generation Backend"
    app_env: str = "development"
    gen_app_debug: bool = True

    gcp_project_id: str = ""
    gcp_location: str = "global"
    generated_dir: str = "/workspace/frontend/public/generated"
    gcp_vertex_image_model: str = "gemini-3-pro-image-preview"
    gcp_vertex_video_model: str = "veo-3.1-generate-preview"
    gcp_vertex_audio_model: str = "gemini-2.5-flash-preview-tts"
    scene_planner_model: str = "gemini-2.5-pro"
    creator_reference_model: str = "gemini-2.5-pro"
    creator_reference_search_enabled: bool = True
    max_scene_plan_attempts: int = 1
    max_image_text_retry: int = 2
    max_allowed_text_chars_frame: int = 12
    max_allowed_text_chars_thumbnail: int = 12
    max_image_generation_attempts: int = 5
    image_retry_backoff_base_sec: float = 4.0
    image_retry_backoff_max_sec: float = 30.0
    image_request_interval_sec: float = 1.2
    output_image_width: int = 640
    output_image_height: int = 360
    preview_video_fps: int = 10
    preview_video_bitrate: str = "550k"
    max_worker_jobs: int = 1
    default_max_video_seconds: int = 5
    video_quality_threshold: float = 0.55
    max_video_attempts: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()

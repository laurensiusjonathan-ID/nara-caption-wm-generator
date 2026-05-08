"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Video Caption Watermark API"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # API
    api_v1_prefix: str = "/api/v1"
    
    # Storage paths
    storage_base_path: Path = Path("./storage")
    uploads_path: Path = Path("./storage/uploads")
    watermarks_path: Path = Path("./storage/watermarks")
    captions_path: Path = Path("./storage/captions")
    outputs_path: Path = Path("./storage/outputs")
    
    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 3600  # 1 hour
    
    # Video processing
    max_upload_size_mb: int = 500
    supported_video_formats: list[str] = ["mp4", "mov", "avi"]
    supported_watermark_formats: list[str] = ["png"]
    
    # Caption generation
    default_caption_language: str = "id"  # Indonesian
    default_caption_format: str = "srt"
    whisper_model_size: str = "base"  # tiny, base, small, medium, large
    
    # FFmpeg
    ffmpeg_threads: int = 4
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        """Initialize settings and create storage directories."""
        super().__init__(**kwargs)
        self._create_storage_directories()
    
    def _create_storage_directories(self):
        """Create storage directories if they don't exist."""
        for path in [
            self.storage_base_path,
            self.uploads_path,
            self.watermarks_path,
            self.captions_path,
            self.outputs_path
        ]:
            path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

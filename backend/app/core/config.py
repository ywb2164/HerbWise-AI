from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "HerbWise AI API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "mysql+asyncmy://herbwise:herbwise@db:3306/herbwise"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: SecretStr = SecretStr("replace-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=60, ge=1)
    ai_mode: str = "mock"
    rag_mode: str = "mock"
    yolo_mode: str = "mock"
    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    text_model: str = ""
    vision_model: str = ""
    review_model: str = ""
    ragflow_base_url: str = ""
    ragflow_api_key: SecretStr = SecretStr("")
    ragflow_dataset_id: str = ""
    upload_dir: Path = Path("/data/uploads")
    report_dir: Path = Path("/data/reports")
    model_dir: Path = Path("/data/models")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()

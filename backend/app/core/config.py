from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "HerbWise AI API"
    app_env: str = "development"
    app_timezone: str = "Asia/Shanghai"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "mysql+asyncmy://herbwise:herbwise@db:3306/herbwise"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: SecretStr = SecretStr("development-only-change-me-32-bytes")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=60, ge=1)
    jwt_refresh_expire_days: int = Field(default=7, ge=1)
    ai_mode: str = "mock"
    rag_mode: str = "mock"
    yolo_mode: str = "mock"
    vision_mode: str = "mock"
    llm_mode: str = "mock"
    model_api_base_url: str = ""
    model_api_key: SecretStr = SecretStr("")
    qwen_vl_model: str = ""
    generation_model: str = ""
    model_connect_timeout_seconds: float = Field(default=10, gt=0)
    model_read_timeout_seconds: float = Field(default=45, gt=0)
    model_max_retries: int = Field(default=1, ge=0, le=3)
    local_vision_enabled: bool = False
    local_model_type: str = "ultralytics"
    local_model_path: str = ""
    local_model_device: str = "auto"
    local_model_image_size: int = Field(default=640, ge=32)
    local_model_confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    local_model_top_k: int = Field(default=3, ge=1, le=10)
    fusion_agreement_bonus: float = Field(default=0.15, ge=0, le=1)
    fusion_conflict_penalty: float = Field(default=0.15, ge=0, le=1)
    fusion_confidence_cap: float = Field(default=0.99, ge=0, le=1)
    fusion_local_accept_threshold: float = Field(default=0.55, ge=0, le=1)
    real_ai_tests_enabled: bool = False
    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    text_model: str = ""
    vision_model: str = ""
    review_model: str = ""
    ragflow_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("RAGFLOW_BASE_URL", "RAGFLOW_API_BASE_URL"),
    )
    ragflow_api_key: SecretStr = SecretStr("")
    ragflow_dataset_id: str = ""
    ragflow_dataset_name: str = ""
    ragflow_connect_timeout_seconds: float = Field(default=10, gt=0)
    ragflow_read_timeout_seconds: float = Field(default=60, gt=0)
    ragflow_max_retries: int = Field(default=1, ge=0, le=3)
    ragflow_top_k: int = Field(default=8, ge=1, le=20)
    ragflow_score_threshold: float = Field(default=0.25, ge=0, le=1)
    ragflow_rerank_enabled: bool = True
    ragflow_vector_weight: float = Field(default=0.70, ge=0, le=1)
    ragflow_keyword_weight: float = Field(default=0.30, ge=0, le=1)
    rag_max_evidence_items: int = Field(default=8, ge=1, le=20)
    rag_max_evidence_characters: int = Field(default=12000, ge=256)
    rag_cache_ttl_seconds: int = Field(default=3600, ge=1)
    rag_replay_enabled: bool = True
    demo_replay_enabled: bool = True
    demo_replay_code: str = ""
    demo_test_image_path: str = ""
    real_rag_tests_enabled: bool = False
    real_full_loop_tests_enabled: bool = False
    run_mode: str = "mock"
    upload_dir: Path = Path("/data/uploads")
    report_dir: Path = Path("/data/reports")
    report_output_dir: Path | None = None
    report_template_dir: Path = Path("templates/reports")
    model_dir: Path = Path("/data/models")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)

    def effective_vision_mode(self) -> str:
        return self.vision_mode if self.vision_mode != "mock" else self.yolo_mode

    def effective_report_dir(self) -> Path:
        """Keep the legacy REPORT_DIR working while accepting V0.4 naming."""
        return self.report_output_dir or self.report_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()

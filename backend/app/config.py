from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DocFlow 智文通"
    app_env: str = "production"
    api_prefix: str = "/api"
    log_level: str = "INFO"

    database_url: str = (
        "mysql+pymysql://root:root@127.0.0.1:3306/docflow?charset=utf8mb4"
    )
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12

    captcha_expire_seconds: int = 180
    upload_dir: Path = BACKEND_DIR / "data" / "uploads"
    upload_max_mb: int = 30

    qwen_api_key: str = Field(default_factory=lambda: os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("API_KEY", ""))
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_chat_model: str = "qwen-max"
    qwen_embedding_model: str = "text-embedding-v3"
    qwen_vision_model: str = "qwen-vl-max"
    embedding_provider: str = "bge_m3"
    bge_m3_model: str = "BAAI/bge-m3"
    bge_device: str = "cpu"
    bge_batch_size: int = 8
    bge_local_files_only: bool = True
    reranker_enabled: bool = True
    bge_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_top_n: int = 20
    embedding_dim: int = 1024

    redis_enabled: bool = Field(default_factory=lambda: _env_bool("REDIS_ENABLED", True))
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    redis_embedding_ttl_seconds: int = 86400
    redis_answer_ttl_seconds: int = 3600
    redis_socket_timeout: float = 0.8
    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    milvus_database: str = "default"
    milvus_collection: str = "docflow_chunks"

    retrieval_top_k: int = 6
    dense_top_k: int = 20
    bm25_top_k: int = 20
    max_context_chars: int = 12000
    default_history_turns: int = 5

    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def is_test(self) -> bool:
        return self.app_env.lower() == "test"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()

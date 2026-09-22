"""VisionOps configuration management.

All configuration is loaded from environment variables with sensible defaults.
See .env.example for available settings.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic_settings import BaseSettings


class VisionOpsSettings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # Environment
    visionops_env: str = "development"

    # vLLM Model Server
    vllm_base_url: str = "http://localhost:8000/v1"
    vision_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    model_timeout: int = 120
    model_max_tokens: int = 4096

    # Agent Configuration
    max_refinement_iterations: int = 2

    # Storage
    upload_dir: Path = Path("./data/uploads")
    page_dir: Path = Path("./data/pages")
    output_dir: Path = Path("./data/outputs")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    cors_origins: list[str] = ["http://localhost:3000"]

    # Upload Limits
    max_upload_size_mb: int = 50

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create data directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.page_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> VisionOpsSettings:
    """Create and return application settings."""
    return VisionOpsSettings()

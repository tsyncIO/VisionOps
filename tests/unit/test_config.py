"""Unit tests for VisionOps configuration."""

from __future__ import annotations

import os

from packages.core.config import VisionOpsSettings


class TestSettings:
    def test_defaults(self):
        settings = VisionOpsSettings()
        assert settings.visionops_env == "development"
        assert settings.api_port == 8001
        assert settings.max_refinement_iterations == 2
        assert settings.vision_model == "Qwen/Qwen2.5-VL-7B-Instruct"

    def test_max_upload_size_bytes(self):
        settings = VisionOpsSettings()
        assert settings.max_upload_size_bytes == 50 * 1024 * 1024

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("VISION_MODEL", "test-model")
        monkeypatch.setenv("API_PORT", "9999")
        settings = VisionOpsSettings()
        assert settings.vision_model == "test-model"
        assert settings.api_port == 9999

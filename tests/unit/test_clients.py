"""Unit tests for the vision model client subsystem.

Tests cover:
- Exception hierarchy
- Image encoding and data URL generation
- JSON extraction from model responses
- Structured output instruction building
- OpenAI message construction
- Mock client behavior (sequential, keyed, failure)
- Structured output parsing with Pydantic
- OpenAI client error handling (unavailable, timeout, bad response)
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import BaseModel

from packages.core.clients import (
    ModelOutputInvalidError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
    VisionModelError,
)
from packages.core.clients.openai_client import (
    OpenAICompatibleVisionModelClient,
    _build_structured_output_instruction,
    _encode_image_to_data_url,
    _extract_json_from_response,
)


# ---------------------------------------------------------------------------
# Test models for structured output
# ---------------------------------------------------------------------------

class SimpleModel(BaseModel):
    name: str
    value: int


class ConceptModel(BaseModel):
    id: str
    name: str
    description: str


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_base_exception(self):
        err = VisionModelError("test error")
        assert err.message == "test error"
        assert err.code == "MODEL_ERROR"
        assert str(err) == "test error"

    def test_unavailable_error(self):
        err = ModelUnavailableError()
        assert err.code == "MODEL_UNAVAILABLE"
        assert "unavailable" in err.message.lower()

    def test_timeout_error_without_value(self):
        err = ModelTimeoutError()
        assert err.code == "MODEL_TIMEOUT"
        assert err.timeout is None

    def test_timeout_error_with_value(self):
        err = ModelTimeoutError(timeout=30.0)
        assert err.timeout == 30.0
        assert "30.0s" in err.message

    def test_output_invalid_error(self):
        err = ModelOutputInvalidError(raw_output='{"bad": true}')
        assert err.code == "MODEL_OUTPUT_INVALID"
        assert err.raw_output == '{"bad": true}'

    def test_response_error(self):
        err = ModelResponseError("Server error", status_code=500)
        assert err.code == "MODEL_RESPONSE_ERROR"
        assert err.status_code == 500

    def test_all_inherit_from_base(self):
        for cls in [ModelUnavailableError, ModelTimeoutError,
                    ModelOutputInvalidError, ModelResponseError]:
            assert issubclass(cls, VisionModelError)


# ---------------------------------------------------------------------------
# Image Encoding Tests
# ---------------------------------------------------------------------------

class TestImageEncoding:
    def test_encode_bytes(self):
        raw_bytes = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes
        result = _encode_image_to_data_url(raw_bytes)
        assert result.startswith("data:image/png;base64,")
        # Verify round-trip
        encoded_part = result.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert decoded == raw_bytes

    def test_encode_file_path(self, tmp_path):
        # Create a temporary image file
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-png-data")
        result = _encode_image_to_data_url(str(img_file))
        assert result.startswith("data:image/png;base64,")

    def test_encode_jpeg_file(self, tmp_path):
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"fake-jpeg-data")
        result = _encode_image_to_data_url(str(img_file))
        assert result.startswith("data:image/jpeg;base64,")

    def test_encode_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            _encode_image_to_data_url("/nonexistent/image.png")


# ---------------------------------------------------------------------------
# JSON Extraction Tests
# ---------------------------------------------------------------------------

class TestJsonExtraction:
    def test_plain_json(self):
        result = _extract_json_from_response('{"name": "test", "value": 42}')
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_json_in_markdown_fence(self):
        text = '```json\n{"name": "test", "value": 42}\n```'
        result = _extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_json_in_generic_fence(self):
        text = '```\n{"name": "test"}\n```'
        result = _extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_json_with_preamble(self):
        text = 'Here is the result:\n\n{"name": "test", "value": 1}'
        result = _extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["name"] == "test"

    def test_json_array(self):
        text = '[{"id": 1}, {"id": 2}]'
        result = _extract_json_from_response(text)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_nested_json(self):
        text = '{"outer": {"inner": {"deep": true}}}'
        result = _extract_json_from_response(text)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"]["deep"] is True

    def test_plain_text_fallback(self):
        text = "Just some plain text"
        result = _extract_json_from_response(text)
        assert result == "Just some plain text"


# ---------------------------------------------------------------------------
# Structured Output Instruction Tests
# ---------------------------------------------------------------------------

class TestStructuredOutputInstruction:
    def test_includes_schema(self):
        instruction = _build_structured_output_instruction(SimpleModel)
        assert "JSON Schema" in instruction
        assert "name" in instruction
        assert "value" in instruction

    def test_includes_format_directive(self):
        instruction = _build_structured_output_instruction(SimpleModel)
        assert "valid JSON" in instruction
        assert "ONLY" in instruction


# ---------------------------------------------------------------------------
# OpenAI Client Message Building Tests
# ---------------------------------------------------------------------------

class TestOpenAIClientMessageBuilding:
    def setup_method(self):
        self.client = OpenAICompatibleVisionModelClient(
            base_url="http://test:8000/v1",
            model="test-model",
        )

    def test_text_only_messages(self):
        messages = self.client._build_messages(
            system_prompt="You are a helpful assistant",
            images=[],
            text="Hello world",
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello world"

    def test_image_messages(self, tmp_path):
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-image")

        messages = self.client._build_messages(
            system_prompt="Analyze this",
            images=[str(img_file)],
            text=None,
        )
        assert len(messages) == 2
        user_content = messages[1]["content"]
        assert isinstance(user_content, list)
        assert user_content[0]["type"] == "image_url"
        assert user_content[0]["image_url"]["url"].startswith("data:image/png;base64,")

    def test_multimodal_messages(self, tmp_path):
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-image")

        messages = self.client._build_messages(
            system_prompt="Analyze",
            images=[str(img_file)],
            text="Additional context",
        )
        user_content = messages[1]["content"]
        assert isinstance(user_content, list)
        assert len(user_content) == 2  # image + text
        assert user_content[0]["type"] == "image_url"
        assert user_content[1]["type"] == "text"
        assert user_content[1]["text"] == "Additional context"

    def test_structured_output_adds_schema(self):
        messages = self.client._build_messages(
            system_prompt="Extract data",
            images=[],
            text="test input",
            response_model=SimpleModel,
        )
        system_content = messages[0]["content"]
        assert "JSON Schema" in system_content
        assert "name" in system_content


# ---------------------------------------------------------------------------
# OpenAI Client HTTP Error Handling Tests
# ---------------------------------------------------------------------------

class TestOpenAIClientErrors:
    def setup_method(self):
        self.client = OpenAICompatibleVisionModelClient(
            base_url="http://test:8000/v1",
            model="test-model",
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_connection_error(self):
        with patch.object(
            self.client._client, "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(ModelUnavailableError) as exc_info:
                await client_analyze_text(self.client)
            assert "Cannot connect" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        with patch.object(
            self.client._client, "post",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(ModelTimeoutError) as exc_info:
                await client_analyze_text(self.client)
            assert exc_info.value.timeout == 5.0

    @pytest.mark.asyncio
    async def test_server_error_response(self):
        mock_response = httpx.Response(
            status_code=500,
            json={"error": {"message": "Internal error"}},
            request=httpx.Request("POST", "http://test/v1/chat/completions"),
        )
        with patch.object(self.client._client, "post", return_value=mock_response):
            with pytest.raises(ModelResponseError) as exc_info:
                await client_analyze_text(self.client)
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_successful_text_response(self):
        mock_response = httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": "Hello from model"}}],
            },
            request=httpx.Request("POST", "http://test/v1/chat/completions"),
        )
        with patch.object(self.client._client, "post", return_value=mock_response):
            result = await self.client.analyze_text("input", "prompt")
            assert result == "Hello from model"

    @pytest.mark.asyncio
    async def test_successful_structured_response(self):
        model_output = json.dumps({"name": "encoder", "value": 42})
        mock_response = httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": model_output}}],
            },
            request=httpx.Request("POST", "http://test/v1/chat/completions"),
        )
        with patch.object(self.client._client, "post", return_value=mock_response):
            result = await self.client.analyze_text(
                "input", "prompt", response_model=SimpleModel
            )
            assert isinstance(result, SimpleModel)
            assert result.name == "encoder"
            assert result.value == 42

    @pytest.mark.asyncio
    async def test_structured_response_with_markdown_fence(self):
        model_output = '```json\n{"name": "test", "value": 1}\n```'
        mock_response = httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": model_output}}],
            },
            request=httpx.Request("POST", "http://test/v1/chat/completions"),
        )
        with patch.object(self.client._client, "post", return_value=mock_response):
            result = await self.client.analyze_text(
                "input", "prompt", response_model=SimpleModel
            )
            assert isinstance(result, SimpleModel)
            assert result.name == "test"

    @pytest.mark.asyncio
    async def test_malformed_response_structure(self):
        mock_response = httpx.Response(
            status_code=200,
            json={"unexpected": "format"},
            request=httpx.Request("POST", "http://test/v1/chat/completions"),
        )
        with patch.object(self.client._client, "post", return_value=mock_response):
            with pytest.raises(ModelResponseError) as exc_info:
                await client_analyze_text(self.client)
            assert "Unexpected response" in exc_info.value.message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def client_analyze_text(client: OpenAICompatibleVisionModelClient) -> str:
    """Helper to make a simple text analysis call."""
    return await client.analyze_text("test input", "test prompt")

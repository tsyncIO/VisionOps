"""Mock vision model client for testing.

Returns pre-configured responses without requiring a GPU or model server.
Used by unit tests and integration tests to exercise the full agent pipeline
with deterministic, predictable VLM outputs.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from packages.core.clients import ModelOutputInvalidError
from packages.core.clients.base import VisionModelClient

logger = logging.getLogger("visionops.mock_client")

T = TypeVar("T", bound=BaseModel)


class MockVisionModelClient(VisionModelClient):
    """Mock VLM client that returns pre-configured responses.

    Usage:
        # Simple text response
        client = MockVisionModelClient(default_response="Hello")

        # Structured response matching a Pydantic model
        client = MockVisionModelClient(
            default_response=json.dumps({"id": "enc", "name": "Encoder", ...})
        )

        # Different responses for sequential calls
        client = MockVisionModelClient(
            responses=["first call", "second call", "third call"]
        )

        # Response keyed by a substring in the prompt
        client = MockVisionModelClient(
            response_map={
                "concept": '{"concepts": [...]}',
                "relationship": '{"relationships": [...]}',
            }
        )
    """

    def __init__(
        self,
        default_response: str = "",
        responses: list[str] | None = None,
        response_map: dict[str, str] | None = None,
        should_fail: bool = False,
        failure_error: Exception | None = None,
    ):
        """Initialize the mock client.

        Args:
            default_response: Default text response for any call.
            responses: Sequential responses (consumed in order).
            response_map: Map of prompt substrings to responses.
            should_fail: If True, raise failure_error on every call.
            failure_error: Exception to raise when should_fail is True.
        """
        self.default_response = default_response
        self.responses = list(responses) if responses else []
        self.response_map = response_map or {}
        self.should_fail = should_fail
        self.failure_error = failure_error or ModelOutputInvalidError("Mock failure")

        # Track calls for test assertions
        self.calls: list[dict[str, Any]] = []
        self._call_index = 0

    def _get_response(self, prompt: str) -> str:
        """Determine which response to return based on configuration."""
        if self.should_fail:
            raise self.failure_error

        # Check sequential responses first
        if self.responses and self._call_index < len(self.responses):
            response = self.responses[self._call_index]
            self._call_index += 1
            return response

        # Check prompt-keyed responses
        for key, response in self.response_map.items():
            if key.lower() in prompt.lower():
                return response

        return self.default_response

    def _record_call(self, method: str, **kwargs: Any) -> None:
        """Record a call for test assertions."""
        self.calls.append({"method": method, **kwargs})

    async def analyze_image(
        self,
        image: str | bytes,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        self._record_call(
            "analyze_image", image=image, prompt=prompt,
            response_model=response_model, max_tokens=max_tokens,
        )
        raw = self._get_response(prompt)
        if response_model is None:
            return raw
        return self._parse(raw, response_model)

    async def analyze_text(
        self,
        text: str,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        self._record_call(
            "analyze_text", text=text, prompt=prompt,
            response_model=response_model, max_tokens=max_tokens,
        )
        raw = self._get_response(prompt)
        if response_model is None:
            return raw
        return self._parse(raw, response_model)

    async def analyze_multimodal(
        self,
        images: list[str | bytes],
        text: str,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        self._record_call(
            "analyze_multimodal", images=images, text=text,
            prompt=prompt, response_model=response_model, max_tokens=max_tokens,
        )
        raw = self._get_response(prompt)
        if response_model is None:
            return raw
        return self._parse(raw, response_model)

    @staticmethod
    def _parse(raw: str, response_model: type[T]) -> T:
        """Parse raw JSON text into a Pydantic model."""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ModelOutputInvalidError(
                message=f"Mock response is not valid JSON: {e}",
                raw_output=raw,
            )
        try:
            return response_model.model_validate(parsed)
        except ValidationError as e:
            raise ModelOutputInvalidError(
                message=f"Mock response doesn't match {response_model.__name__}: {e}",
                raw_output=raw,
            )

    async def close(self) -> None:
        pass

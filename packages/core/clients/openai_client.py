"""OpenAI-compatible vision model client.

Communicates with vLLM (or any OpenAI-compatible server) through its
HTTP chat completions API. Handles image encoding, structured output
parsing, timeout enforcement, and retry-on-validation-failure.

Architecture:
    Agent Node → VisionModelClient (interface)
                        ↓
              OpenAICompatibleVisionModelClient
                        ↓
              HTTP POST /v1/chat/completions
                        ↓
              vLLM / any OpenAI-compatible server
"""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from packages.core.clients import (
    ModelOutputInvalidError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from packages.core.clients.base import VisionModelClient

logger = logging.getLogger("visionops.client")

T = TypeVar("T", bound=BaseModel)


def _encode_image_to_data_url(image: str | bytes) -> str:
    """Convert an image file path or raw bytes to a base64 data URL.

    Args:
        image: Either a file path (str) or raw image bytes.

    Returns:
        A data URL string like 'data:image/png;base64,...'
    """
    if isinstance(image, str):
        path = Path(image)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image}")
        image_bytes = path.read_bytes()
        # Determine MIME type from extension
        suffix = path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".svg": "image/svg+xml",
        }
        mime_type = mime_map.get(suffix, "image/png")
    else:
        image_bytes = image
        mime_type = "image/png"

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _build_structured_output_instruction(response_model: type[BaseModel]) -> str:
    """Build a prompt suffix instructing the model to output valid JSON.

    Includes the Pydantic model's JSON schema so the VLM knows exactly
    what structure to produce.
    """
    schema = response_model.model_json_schema()
    return (
        "\n\n---\n"
        "IMPORTANT: You MUST respond with valid JSON that conforms to this schema. "
        "Output ONLY the JSON object, no markdown fences, no explanation.\n\n"
        f"JSON Schema:\n```json\n{json.dumps(schema, indent=2)}\n```"
    )


def _extract_json_from_response(text: str) -> str:
    """Extract JSON from model response, handling markdown fences and preamble.

    Models sometimes wrap JSON in ```json ... ``` or add text before/after.
    This function extracts the JSON object or array.
    """
    # Try to find JSON in markdown code blocks first
    fence_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(fence_pattern, text)
    if matches:
        return matches[0].strip()

    # Try to find a JSON object or array directly
    # Pick whichever bracket type appears first in the text
    obj_idx = text.find("{")
    arr_idx = text.find("[")

    candidates: list[tuple[int, str, str]] = []
    if obj_idx != -1:
        candidates.append((obj_idx, "{", "}"))
    if arr_idx != -1:
        candidates.append((arr_idx, "[", "]"))

    # Sort by position — try the earliest match first
    candidates.sort(key=lambda x: x[0])

    for start_idx, start_char, end_char in candidates:
        # Find the matching closing bracket by counting depth
        depth = 0
        for i in range(start_idx, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]

    # Fall back to the raw text
    return text.strip()


class OpenAICompatibleVisionModelClient(VisionModelClient):
    """Vision model client that uses the OpenAI-compatible chat completions API.

    This client communicates with vLLM or any server exposing the same API.
    It handles:
    - Image encoding to base64 data URLs
    - Multimodal message construction
    - Structured output via JSON schema in prompt
    - Pydantic validation of responses
    - One retry on validation failure (with error feedback)
    - Timeout enforcement
    - Structured error handling (never crashes the API)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-VL-7B-Instruct",
        timeout: float = 120.0,
        max_tokens: int = 4096,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.default_max_tokens = max_tokens
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ----- Public API (implements VisionModelClient) -----

    async def analyze_image(
        self,
        image: str | bytes,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        """Analyze a single image with a text prompt."""
        messages = self._build_messages(
            system_prompt=prompt,
            images=[image],
            text=None,
            response_model=response_model,
        )
        return await self._complete(messages, response_model, max_tokens)

    async def analyze_text(
        self,
        text: str,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        """Analyze text-only input with a prompt."""
        messages = self._build_messages(
            system_prompt=prompt,
            images=[],
            text=text,
            response_model=response_model,
        )
        return await self._complete(messages, response_model, max_tokens)

    async def analyze_multimodal(
        self,
        images: list[str | bytes],
        text: str,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        """Analyze multiple images with text context and a prompt."""
        messages = self._build_messages(
            system_prompt=prompt,
            images=images,
            text=text,
            response_model=response_model,
        )
        return await self._complete(messages, response_model, max_tokens)

    # ----- Internal Methods -----

    def _build_messages(
        self,
        system_prompt: str,
        images: list[str | bytes],
        text: str | None,
        response_model: type[BaseModel] | None = None,
    ) -> list[dict[str, Any]]:
        """Build the OpenAI-compatible messages array.

        For multimodal requests, user content is a list of content parts
        (text + image_url entries). For text-only, it's a simple string.
        """
        # System message with optional structured output instruction
        system_content = system_prompt
        if response_model is not None:
            system_content += _build_structured_output_instruction(response_model)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
        ]

        # Build user content parts
        user_content: list[dict[str, Any]] = []

        # Add images
        for img in images:
            data_url = _encode_image_to_data_url(img)
            user_content.append({
                "type": "image_url",
                "image_url": {"url": data_url},
            })

        # Add text
        if text:
            user_content.append({"type": "text", "text": text})
        elif not images:
            # Text-only case shouldn't have empty content
            user_content.append({"type": "text", "text": "(no additional context)"})

        # If there are no images, simplify to string content
        if not images and text:
            messages.append({"role": "user", "content": text})
        else:
            messages.append({"role": "user", "content": user_content})

        return messages

    async def _complete(
        self,
        messages: list[dict[str, Any]],
        response_model: type[T] | None,
        max_tokens: int | None,
    ) -> str | T:
        """Send a chat completion request and optionally parse into a Pydantic model.

        On validation failure, retries once with the error message appended
        to help the model self-correct.
        """
        raw_text = await self._send_request(messages, max_tokens)

        if response_model is None:
            return raw_text

        # Attempt to parse structured output
        try:
            return self._parse_structured_output(raw_text, response_model)
        except ModelOutputInvalidError as first_error:
            logger.warning(
                "First parse attempt failed, retrying with error feedback: %s",
                first_error.message,
            )

        # Retry: append the error and raw output to help the model correct itself
        retry_messages = messages + [
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": (
                    f"Your previous response could not be parsed as valid JSON. "
                    f"Error: {first_error.message}\n\n"
                    f"Please respond with ONLY a valid JSON object matching the schema. "
                    f"No markdown, no explanation, just the JSON."
                ),
            },
        ]

        retry_text = await self._send_request(retry_messages, max_tokens)

        try:
            return self._parse_structured_output(retry_text, response_model)
        except ModelOutputInvalidError:
            # Both attempts failed — raise with both raw outputs for debugging
            raise ModelOutputInvalidError(
                message=(
                    f"Model output could not be validated after retry. "
                    f"Schema: {response_model.__name__}"
                ),
                raw_output=retry_text,
            )

    async def _send_request(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
    ) -> str:
        """Send the HTTP request to the model server and return raw text content."""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": 0.1,  # Low temperature for structured output
        }

        url = f"{self.base_url}/chat/completions"

        try:
            response = await self._client.post(url, json=payload)
        except httpx.ConnectError as e:
            raise ModelUnavailableError(
                f"Cannot connect to model server at {self.base_url}: {e}"
            )
        except httpx.TimeoutException:
            raise ModelTimeoutError(timeout=self.timeout)

        if response.status_code != 200:
            # Try to extract error message from response body
            try:
                error_body = response.json()
                error_msg = error_body.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            raise ModelResponseError(
                message=f"Model server error ({response.status_code}): {error_msg}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except Exception as e:
            raise ModelResponseError(f"Invalid JSON response from model server: {e}")

        # Extract the content from the OpenAI-compatible response
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ModelResponseError(
                f"Unexpected response structure from model server: {e}"
            )

        return content

    def _parse_structured_output(self, raw_text: str, response_model: type[T]) -> T:
        """Parse raw model text into a validated Pydantic model.

        Handles JSON extraction from markdown fences, preamble text, etc.
        """
        json_str = _extract_json_from_response(raw_text)

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ModelOutputInvalidError(
                message=f"Response is not valid JSON: {e}",
                raw_output=raw_text,
            )

        try:
            return response_model.model_validate(parsed)
        except ValidationError as e:
            raise ModelOutputInvalidError(
                message=f"JSON does not match {response_model.__name__} schema: {e}",
                raw_output=raw_text,
            )

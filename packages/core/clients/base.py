"""Vision model client protocol.

Defines the abstract interface that all model clients must implement.
The agent graph depends on this interface, NOT on a specific model server.
This allows swapping vLLM for another OpenAI-compatible server, a remote API,
or a mock client for testing — without changing agent code.
"""

from __future__ import annotations

import abc
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class VisionModelClient(abc.ABC):
    """Abstract base class for vision model clients.

    All agent nodes that need VLM inference depend on this interface.
    Implementations handle the specifics of communicating with a model server.
    """

    @abc.abstractmethod
    async def analyze_image(
        self,
        image: str | bytes,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        """Analyze a single image with a text prompt.

        Args:
            image: File path (str) or raw bytes of the image.
            prompt: The text prompt for the VLM.
            response_model: Optional Pydantic model to parse the response into.
            max_tokens: Optional override for max output tokens.

        Returns:
            Raw text response if response_model is None,
            otherwise a validated Pydantic model instance.

        Raises:
            ModelUnavailableError: If the model server is unreachable.
            ModelTimeoutError: If the request times out.
            ModelOutputInvalidError: If the response cannot be parsed/validated.
            ModelResponseError: If the server returns an error.
        """
        ...

    @abc.abstractmethod
    async def analyze_text(
        self,
        text: str,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        """Analyze text-only input with a prompt.

        Args:
            text: The input text to analyze.
            prompt: The system/instruction prompt.
            response_model: Optional Pydantic model for structured output.
            max_tokens: Optional override for max output tokens.

        Returns:
            Raw text or validated Pydantic model instance.
        """
        ...

    @abc.abstractmethod
    async def analyze_multimodal(
        self,
        images: list[str | bytes],
        text: str,
        prompt: str,
        response_model: type[T] | None = None,
        max_tokens: int | None = None,
    ) -> str | T:
        """Analyze multiple images with text context and a prompt.

        Args:
            images: List of image file paths or raw bytes.
            text: Additional text context.
            prompt: The system/instruction prompt.
            response_model: Optional Pydantic model for structured output.
            max_tokens: Optional override for max output tokens.

        Returns:
            Raw text or validated Pydantic model instance.
        """
        ...

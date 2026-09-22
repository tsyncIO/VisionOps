"""VisionOps model client exceptions.

Structured error types for model communication failures.
These are used by the model client and surfaced through the API
as structured error responses — never as raw stack traces.
"""

from __future__ import annotations


class VisionModelError(Exception):
    """Base exception for all model client errors."""

    def __init__(self, message: str, code: str = "MODEL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ModelUnavailableError(VisionModelError):
    """The model server (vLLM) is unreachable."""

    def __init__(self, message: str = "Model server is unavailable"):
        super().__init__(message, code="MODEL_UNAVAILABLE")


class ModelTimeoutError(VisionModelError):
    """The model request timed out."""

    def __init__(self, message: str = "Model request timed out", timeout: float | None = None):
        self.timeout = timeout
        if timeout is not None:
            message = f"{message} (after {timeout}s)"
        super().__init__(message, code="MODEL_TIMEOUT")


class ModelOutputInvalidError(VisionModelError):
    """The model returned output that could not be parsed or validated."""

    def __init__(
        self,
        message: str = "Model output could not be validated",
        raw_output: str | None = None,
    ):
        self.raw_output = raw_output
        super().__init__(message, code="MODEL_OUTPUT_INVALID")


class ModelResponseError(VisionModelError):
    """The model server returned an error response."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message, code="MODEL_RESPONSE_ERROR")

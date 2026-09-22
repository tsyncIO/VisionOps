"""VisionOps event system.

Structured events emitted during agent execution and streamed to the frontend via SSE.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class VisionOpsEvent(BaseModel):
    """A structured event emitted during agent execution."""

    event: str = Field(..., description="Event type name")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp",
    )
    run_id: str = Field(..., description="Associated run ID")
    data: dict[str, Any] = Field(default_factory=dict, description="Event payload")

    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        return f"event: {self.event}\ndata: {self.model_dump_json()}\n\n"


# Predefined event types
EVENT_RUN_STARTED = "run_started"
EVENT_DOCUMENT_INGESTED = "document_ingested"
EVENT_CONCEPT_EXTRACTION_STARTED = "concept_extraction_started"
EVENT_CONCEPTS_EXTRACTED = "concepts_extracted"
EVENT_RELATIONSHIPS_EXTRACTED = "relationships_extracted"
EVENT_EQUATIONS_EXTRACTED = "equations_extracted"
EVENT_DIAGRAM_PLANNED = "diagram_planned"
EVENT_DIAGRAM_RENDERED = "diagram_rendered"
EVENT_CRITIQUE_STARTED = "critique_started"
EVENT_CRITIQUE_COMPLETED = "critique_completed"
EVENT_REFINEMENT_STARTED = "refinement_started"
EVENT_FINAL_RESULT = "final_result"
EVENT_RUN_COMPLETED = "run_completed"
EVENT_RUN_FAILED = "run_failed"

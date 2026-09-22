"""Unit tests for VisionOps event system."""

from __future__ import annotations

from packages.core.events import VisionOpsEvent, EVENT_CONCEPTS_EXTRACTED


class TestVisionOpsEvent:
    def test_create(self):
        event = VisionOpsEvent(
            event=EVENT_CONCEPTS_EXTRACTED,
            run_id="run-001",
            data={"count": 12},
        )
        assert event.event == "concepts_extracted"
        assert event.run_id == "run-001"
        assert event.data["count"] == 12

    def test_timestamp_auto(self):
        event = VisionOpsEvent(event="test", run_id="r1")
        assert event.timestamp is not None

    def test_to_sse(self):
        event = VisionOpsEvent(
            event="test_event",
            run_id="run-001",
            data={"key": "value"},
        )
        sse = event.to_sse()
        assert sse.startswith("event: test_event\n")
        assert "data:" in sse
        assert sse.endswith("\n\n")

    def test_json_roundtrip(self):
        event = VisionOpsEvent(event="test", run_id="r1", data={"x": 1})
        event2 = VisionOpsEvent.model_validate_json(event.model_dump_json())
        assert event.event == event2.event
        assert event.data == event2.data

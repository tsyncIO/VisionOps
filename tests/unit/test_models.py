"""Unit tests for VisionOps domain models.

Tests cover:
- Model instantiation and serialization
- Field validation and constraints
- DiagramSpec edge reference validation
- JSON round-trip
"""

from __future__ import annotations

import pytest

from packages.core.models import (
    Concept,
    Critique,
    DiagramEdge,
    DiagramNode,
    DiagramSpec,
    Equation,
    Relationship,
    VisionOpsState,
)


# ---------------------------------------------------------------------------
# Concept Tests
# ---------------------------------------------------------------------------

class TestConcept:
    def test_create_minimal(self):
        c = Concept(id="enc", name="Encoder", description="Encodes input")
        assert c.id == "enc"
        assert c.name == "Encoder"
        assert c.role is None
        assert c.equations == []
        assert c.importance is None

    def test_create_full(self):
        c = Concept(
            id="enc",
            name="Encoder",
            description="Encodes input",
            role="processing_component",
            equations=["eq1"],
            importance=0.95,
        )
        assert c.role == "processing_component"
        assert c.importance == 0.95

    def test_importance_bounds(self):
        with pytest.raises(Exception):
            Concept(id="x", name="X", description="X", importance=1.5)
        with pytest.raises(Exception):
            Concept(id="x", name="X", description="X", importance=-0.1)

    def test_json_roundtrip(self):
        c = Concept(id="enc", name="Encoder", description="Encodes input", importance=0.9)
        data = c.model_dump_json()
        c2 = Concept.model_validate_json(data)
        assert c == c2


# ---------------------------------------------------------------------------
# Relationship Tests
# ---------------------------------------------------------------------------

class TestRelationship:
    def test_create(self):
        r = Relationship(
            source="enc", target="latent",
            relationship="produces", direction="forward",
        )
        assert r.source == "enc"
        assert r.direction == "forward"

    def test_json_roundtrip(self):
        r = Relationship(
            source="a", target="b",
            relationship="feeds", direction="bidirectional",
            explanation="A feeds B",
        )
        r2 = Relationship.model_validate_json(r.model_dump_json())
        assert r == r2


# ---------------------------------------------------------------------------
# Equation Tests
# ---------------------------------------------------------------------------

class TestEquation:
    def test_create(self):
        eq = Equation(
            id="eq1", expression="y = f(x)",
            description="Output function",
            related_concepts=["enc"], importance=0.8,
        )
        assert eq.expression == "y = f(x)"

    def test_importance_bounds(self):
        with pytest.raises(Exception):
            Equation(id="e", expression="x", description="x", related_concepts=[], importance=2.0)


# ---------------------------------------------------------------------------
# DiagramSpec Tests
# ---------------------------------------------------------------------------

class TestDiagramSpec:
    def _make_spec(self) -> DiagramSpec:
        return DiagramSpec(
            title="Test Diagram",
            nodes=[
                DiagramNode(id="a", label="Node A"),
                DiagramNode(id="b", label="Node B"),
            ],
            edges=[
                DiagramEdge(source="a", target="b", label="connects"),
            ],
        )

    def test_create(self):
        spec = self._make_spec()
        assert spec.title == "Test Diagram"
        assert len(spec.nodes) == 2
        assert len(spec.edges) == 1
        assert spec.layout == "flowchart"

    def test_get_node_ids(self):
        spec = self._make_spec()
        assert spec.get_node_ids() == {"a", "b"}

    def test_validate_edge_references_valid(self):
        spec = self._make_spec()
        errors = spec.validate_edge_references()
        assert errors == []

    def test_validate_edge_references_invalid(self):
        spec = DiagramSpec(
            title="Bad",
            nodes=[DiagramNode(id="a", label="A")],
            edges=[DiagramEdge(source="a", target="missing")],
        )
        errors = spec.validate_edge_references()
        assert len(errors) == 1
        assert "missing" in errors[0]

    def test_json_roundtrip(self):
        spec = self._make_spec()
        spec2 = DiagramSpec.model_validate_json(spec.model_dump_json())
        assert spec == spec2


# ---------------------------------------------------------------------------
# Critique Tests
# ---------------------------------------------------------------------------

class TestCritique:
    def test_create_passing(self):
        c = Critique(passed=True, score=0.9)
        assert c.passed is True
        assert c.missing_concepts == []

    def test_create_failing(self):
        c = Critique(
            passed=False, score=0.4,
            missing_concepts=["decoder"],
            suggested_changes=["Add decoder node"],
        )
        assert not c.passed
        assert "decoder" in c.missing_concepts

    def test_score_bounds(self):
        with pytest.raises(Exception):
            Critique(passed=True, score=1.5)


# ---------------------------------------------------------------------------
# VisionOpsState Tests
# ---------------------------------------------------------------------------

class TestVisionOpsState:
    def test_create_minimal(self):
        state = VisionOpsState(
            run_id="test-001",
            skill="technical_document_to_diagram",
        )
        assert state.status == "pending"
        assert state.iteration == 0
        assert state.max_iterations == 2
        assert state.concepts == []
        assert state.diagram_spec is None

    def test_json_roundtrip(self):
        state = VisionOpsState(
            run_id="test-001",
            skill="technical_document_to_diagram",
            concepts=[Concept(id="enc", name="Encoder", description="Encodes")],
        )
        state2 = VisionOpsState.model_validate_json(state.model_dump_json())
        assert state == state2

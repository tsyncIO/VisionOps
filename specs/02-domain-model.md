# 02 — Domain Model Specification

## Purpose

Define the Pydantic data models that represent the structured state of VisionOps.

## Requirements

- All important state must be typed using Pydantic v2 models
- No arbitrary dictionaries for meaningful data
- All VLM outputs must be validated through these models
- Models must support JSON serialization for API responses and SSE events

## Models

### Concept

```python
class Concept(BaseModel):
    id: str
    name: str
    description: str
    role: str | None = None
    equations: list[str] = []
    importance: float | None = None
```

### Relationship

```python
class Relationship(BaseModel):
    source: str          # Concept ID
    target: str          # Concept ID
    relationship: str    # e.g., "produces", "feeds_into"
    direction: str       # "forward", "backward", "bidirectional"
    explanation: str | None = None
```

### Equation

```python
class Equation(BaseModel):
    id: str
    expression: str
    description: str
    related_concepts: list[str]   # Concept IDs
    importance: float
```

### DiagramNode

```python
class DiagramNode(BaseModel):
    id: str
    label: str
    description: str | None = None
    type: str = "component"       # component, input, output, process, etc.
```

### DiagramEdge

```python
class DiagramEdge(BaseModel):
    source: str          # DiagramNode ID
    target: str          # DiagramNode ID
    label: str | None = None
    direction: str = "forward"
```

### DiagramSpec

```python
class DiagramSpec(BaseModel):
    title: str
    nodes: list[DiagramNode]
    edges: list[DiagramEdge]
    layout: str = "flowchart"     # flowchart, sequence, etc.
```

### Critique

```python
class Critique(BaseModel):
    passed: bool
    score: float
    missing_concepts: list[str] = []
    incorrect_relationships: list[str] = []
    incorrect_direction: list[str] = []
    missing_equations: list[str] = []
    visual_issues: list[str] = []
    complexity_issues: list[str] = []
    suggested_changes: list[str] = []
```

### VisionOpsState

```python
class VisionOpsState(BaseModel):
    run_id: str
    skill: str
    input_document: str | None = None
    page_images: list[str] = []
    concepts: list[Concept] = []
    relationships: list[Relationship] = []
    equations: list[Equation] = []
    diagram_spec: DiagramSpec | None = None
    rendered_diagram: str | None = None
    critique: Critique | None = None
    iteration: int = 0
    max_iterations: int = 2
    explanation: str | None = None
    status: str = "pending"
    errors: list[str] = []
```

## Constraints

- `DiagramSpec.edges` must only reference node IDs that exist in `DiagramSpec.nodes`
- `Relationship.source` and `Relationship.target` must reference valid Concept IDs
- `Equation.related_concepts` must reference valid Concept IDs
- `Critique.score` is diagnostic only (0.0–1.0)

## Acceptance Criteria

- All models can be instantiated and serialized to JSON
- Validation catches missing required fields
- Models can round-trip through JSON without data loss
- Unit tests cover all model constraints

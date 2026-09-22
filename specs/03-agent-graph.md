# 03 — Agent Graph Specification

## Purpose

Define the LangGraph agent graph structure, node responsibilities, and routing logic.

## Graph Structure

```
START
  ↓
ingest_document
  ↓
extract_concepts
  ↓
extract_relationships
  ↓
extract_equations
  ↓
abstract_system
  ↓
plan_diagram
  ↓
render_diagram
  ↓
visual_critique
  │
  ├── PASS → explain → END
  │
  └── FAIL → refine → plan_diagram
```

## Refinement Loop

- Maximum iterations: configurable, default 2
- Refinement modifies `DiagramSpec`, not the full analysis
- After max iterations, proceed to `explain` regardless of critique result

## Node Specifications

### ingest_document
- **Input:** PDF file path
- **Responsibilities:** Validate PDF, extract pages, convert to images
- **Output:** `page_images` list
- **Event:** `document_ingested`

### extract_concepts
- **Input:** Page images
- **VLM Task:** Identify system concepts from visual content
- **Output:** `list[Concept]`
- **Event:** `concepts_extracted`

### extract_relationships
- **Input:** Page images + concepts
- **VLM Task:** Determine relationships between concepts
- **Output:** `list[Relationship]`
- **Event:** `relationships_extracted`

### extract_equations
- **Input:** Page images + concepts
- **VLM Task:** Extract relevant equations
- **Output:** `list[Equation]`
- **Event:** `equations_extracted`

### abstract_system
- **Input:** Concepts + relationships + equations
- **VLM Task:** Decide what belongs in the diagram, what to omit, and abstraction strategy
- **Output:** Filtered concepts/relationships, abstraction strategy
- **Event:** `system_abstracted`

### plan_diagram
- **Input:** Concepts + relationships + equations + abstraction strategy
- **VLM Task:** Generate structured diagram specification
- **Output:** `DiagramSpec`
- **Event:** `diagram_planned`
- **Constraint:** Must NOT produce SVG/Mermaid code

### render_diagram
- **Input:** `DiagramSpec`
- **Deterministic:** Yes (no VLM)
- **Output:** SVG content/path
- **Event:** `diagram_rendered`

### visual_critique
- **Input:** Source page image + rendered diagram + concepts + relationships + equations
- **VLM Task:** Evaluate diagram quality
- **Output:** `Critique`
- **Event:** `critique_completed`

### refine
- **Input:** `DiagramSpec` + `Critique`
- **VLM Task:** Modify diagram spec based on critique
- **Output:** Updated `DiagramSpec`
- **Event:** `refinement_started`

### explain
- **Input:** All analysis results
- **VLM Task:** Generate human-readable explanation
- **Output:** Explanation text
- **Event:** `run_completed`

## Routing Logic

```python
def should_refine(state: VisionOpsState) -> str:
    if state.critique and state.critique.passed:
        return "explain"
    if state.iteration >= state.max_iterations:
        return "explain"
    return "refine"
```

## Constraints

- Each node has exactly one responsibility
- VLM nodes use prompts from `prompts/` directory
- All VLM output is validated through Pydantic
- Events are emitted at each node transition

## Acceptance Criteria

- Graph can be constructed and compiled by LangGraph
- Routing logic correctly handles PASS, FAIL, and max-iteration scenarios
- Each node produces valid typed output
- Events are emitted for every node execution

# 05 — Rendering Specification

## Purpose

Define how structured `DiagramSpec` objects are converted into visual SVG output.

## Architecture

```
DiagramSpec (Pydantic)
        ↓
  DiagramRenderer (Protocol)
        ↓
  MermaidRenderer (V1 implementation)
        ↓
  Mermaid source code
        ↓
  Mermaid CLI (mmdc) or Mermaid JS
        ↓
  SVG output
```

## Renderer Protocol

```python
class RenderedDiagram(BaseModel):
    svg_content: str
    mermaid_source: str
    output_path: str | None = None

class DiagramRenderer(Protocol):
    def render(self, diagram: DiagramSpec) -> RenderedDiagram: ...
```

## MermaidRenderer Responsibilities

1. **Validate node IDs** — All IDs must be alphanumeric + underscores
2. **Validate edge references** — All edge source/target must reference existing nodes
3. **Sanitize labels** — Escape special characters that break Mermaid syntax
4. **Generate Mermaid source** — Convert DiagramSpec to valid Mermaid flowchart
5. **Render SVG** — Execute Mermaid to produce SVG
6. **Return result** — SVG content + Mermaid source + optional file path

## Mermaid Generation Rules

- Layout `"flowchart"` → `flowchart TD` (top-down)
- Node types map to shapes: `component` → `[]`, `input` → `([])`, `output` → `[[]]`, `process` → `{{}}`
- Edge directions: `forward` → `-->`, `backward` → use reversed source/target, `bidirectional` → `<-->`
- Labels on edges: `-->|label|`

## Error Handling

| Error | Behavior |
|-------|----------|
| Invalid node ID | Sanitize or return structured error |
| Edge references missing node | Return structured rendering error |
| Mermaid CLI failure | Return structured error with Mermaid source for debugging |
| Empty diagram | Return structured error |

## Constraints

- Renderer must never execute arbitrary model-generated code
- Output must be deterministic (same DiagramSpec → same SVG)
- Renderer does not need to understand the original PDF

## Acceptance Criteria

- Valid `DiagramSpec` always produces valid SVG or explicit error
- Invalid `DiagramSpec` never produces corrupted output silently
- Labels with special characters are properly escaped
- Unit tests cover edge cases (empty nodes, self-referencing edges, special chars)

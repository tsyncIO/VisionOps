# 09 — Testing Specification

## Purpose
Define the testing strategy for VisionOps.

## Unit Tests
- Pydantic model validation
- DiagramSpec validation (node refs, edge refs)
- Mermaid source generation
- Graph routing logic
- Configuration loading
- Event serialization

## Integration Tests
- PDF → Agent (mocked VLM) → DiagramSpec → Renderer → Critique
- Use mocked VLM responses (no GPU required)

## End-to-End Tests (Optional, GPU required)
- Real PDF → vLLM → LangGraph → SVG → Critique

## Test Infrastructure
- Framework: pytest + pytest-asyncio
- Fixtures in `tests/fixtures/`
- Mocked VLM client for deterministic testing

## Constraints
- Normal CI tests must NOT require GPU
- GPU tests marked with `@pytest.mark.gpu`
- Tests must be fast (< 30s for unit suite)

## Acceptance Criteria
- `pytest` runs successfully with no GPU
- Unit tests cover all Pydantic models
- Integration tests cover the full mocked pipeline

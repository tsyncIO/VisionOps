# VisionOps Prompts

This directory contains VLM prompt templates used by the agent graph.

Each prompt file defines:
- Role
- Input description
- Task description
- Constraints
- Expected output schema
- Failure behavior

## Files (to be created in Phase 3)

- `concept_extraction.txt` — Extract concepts from document pages
- `relationship_extraction.txt` — Determine relationships between concepts
- `equation_extraction.txt` — Extract relevant equations
- `abstraction.txt` — Decide what belongs in the diagram
- `diagram_planning.txt` — Generate structured DiagramSpec
- `visual_critique.txt` — Critique generated diagram
- `refinement.txt` — Refine DiagramSpec based on critique
- `explanation.txt` — Generate human-readable explanation

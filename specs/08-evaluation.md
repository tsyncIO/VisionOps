# 08 — Evaluation Specification

## Purpose
Define how VisionOps quality is measured.

## Benchmark
10–20 technical documents across: control systems, ML, signal processing, numerical methods, physics, computer architecture.

## Ground Truth
For each document: important concepts, relationships, expected flow, equations.

## Metrics
| Metric | Description |
|--------|-------------|
| Concept Recall | % of ground-truth concepts identified |
| Relationship Accuracy | % of relationships correct |
| Equation Preservation | % of equations captured |
| Diagram Validity | % producing valid SVG |
| Critique Detection | Can critic find deliberate errors? |
| Refinement Success | Does refinement improve diagrams? |
| Latency | Total pipeline time |
| VRAM Usage | Peak GPU memory |

## Acceptance Criteria
- Benchmark docs collected and annotated
- Metrics computable automatically
- Results reproducible

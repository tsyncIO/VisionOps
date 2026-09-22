# 01 — Architecture Specification

## Purpose

Define the high-level system architecture, component boundaries, and communication patterns.

## Architecture Overview

```
┌─────────────────────────────┐
│       Next.js Frontend      │
│       TypeScript/React      │
└──────────────┬──────────────┘
               │ HTTP + SSE
               ▼
┌─────────────────────────────┐
│        FastAPI API          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       VisionOps Core        │
│       LangGraph + Pydantic  │
└──────────────┬──────────────┘
               │ OpenAI-compatible API
               ▼
┌─────────────────────────────┐
│         vLLM Server         │
│    Qwen2.5-VL-7B-Instruct   │
└─────────────────────────────┘
```

## Core Architectural Principle

The VLM performs perception, interpretation, abstraction, reasoning, planning, and critique.

Deterministic software performs validation, rendering, file generation, and graph conversion.

The VLM must NOT directly generate SVG, HTML, Mermaid code, or arbitrary executable rendering code.

```
VLM → Structured DiagramSpec → Pydantic validation → Deterministic renderer → SVG
```

## Component Boundaries

### Frontend (Next.js)
- UI rendering
- Document upload
- SSE event consumption
- Result display

### API Layer (FastAPI)
- HTTP endpoints for documents, runs, results
- SSE streaming endpoint
- Request validation
- CORS configuration

### Core Runtime (Python)
- LangGraph orchestration
- Pydantic state management
- Skill registry
- Event emission

### Model Client
- OpenAI-compatible HTTP client
- Multimodal request formatting
- Structured response parsing
- Timeout/error handling

### Renderer
- DiagramSpec → Mermaid source
- Mermaid → SVG conversion
- Label sanitization and validation

### vLLM Server (External)
- Model inference
- Separate process from application
- Configurable endpoint

## Communication Patterns

| From | To | Protocol |
|------|----|----------|
| Frontend | API | HTTP REST + SSE |
| API | Core | Python function calls |
| Core | vLLM | HTTP (OpenAI-compatible) |
| Core | Renderer | Python function calls |

## Skill Architecture

```
VisionOps Core
      │
      ├── Skill Registry
      │     └── TechnicalDocumentToDiagramSkill (V1)
      │
      ├── Model Client (interface)
      │     └── OpenAICompatibleVisionModelClient
      │
      └── Renderer (protocol)
            └── MermaidRenderer
```

## Constraints

- Single GPU (≈16 GB VRAM)
- One document at a time for V1
- Maximum 2 refinement iterations
- Model name and endpoint must be configurable

## Acceptance Criteria

- Clear separation between VLM reasoning and deterministic rendering
- Model client is swappable via interface
- Renderer is swappable via protocol
- No GPU-specific values are hard-coded
- All configuration via environment variables

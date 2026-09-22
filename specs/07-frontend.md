# 07 — Frontend Specification

## Purpose

Define the Next.js frontend for VisionOps as an AI analysis workspace.

## Technology

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS

## Layout

```
┌──────────────────────────────────────────┐
│ VisionOps                        [Upload]│
├─────────────────┬────────────────────────┤
│                 │                        │
│ Source Document  │ Generated Diagram      │
│ (PDF Viewer)    │ (SVG Viewer)           │
│                 │                        │
├─────────────────┼────────────────────────┤
│ Concepts        │ Relationships          │
│                 │                        │
├─────────────────┴────────────────────────┤
│ Equations                                │
├──────────────────────────────────────────┤
│ Agent Execution Trace                    │
│ ✓ Document analyzed                      │
│ ✓ Concepts extracted (12)                │
│ ⟳ Extracting relationships...           │
└──────────────────────────────────────────┘
```

## Components

```
components/
    upload/DocumentUploader.tsx
    document/PdfViewer.tsx
    diagram/DiagramViewer.tsx
    analysis/ConceptList.tsx
    analysis/RelationshipGraph.tsx
    analysis/EquationList.tsx
    agent/AgentTrace.tsx
    agent/AgentStep.tsx
    critique/CritiquePanel.tsx
    layout/Workspace.tsx
```

## Pages

- `/` — Upload page (landing)
- `/workspace/[runId]` — Analysis workspace

## Data Flow

1. User uploads PDF → `POST /api/documents`
2. User starts analysis → `POST /api/runs`
3. Frontend connects to SSE → `GET /api/runs/{run_id}/events`
4. Events update UI in real-time
5. On completion → `GET /api/runs/{run_id}/result`

## SSE Integration

- Use `EventSource` API or custom hook
- Update agent trace on each event
- Show progress indicators during processing
- Handle disconnect/reconnect

## Design Requirements

- AI analysis workspace aesthetic (not a chatbot)
- Dark mode support
- Responsive layout
- Smooth transitions on agent step completion
- Clear visual hierarchy

## Constraints

- No complex design system for V1
- Keep components focused and reusable
- Frontend runs on port 3000
- Communicates with backend on port 8001

## Acceptance Criteria

- User can upload a PDF without using an API client
- Agent execution trace updates in real-time via SSE
- Source document and generated diagram are displayed side by side
- Concepts, relationships, equations, and critique are visible
- Errors from backend are displayed gracefully

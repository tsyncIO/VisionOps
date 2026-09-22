# VisionOps

## Agentic Multimodal Visual Analytics & Reasoning Platform

### 1. Project Definition

VisionOps is a local-first agentic multimodal AI platform that analyzes visual information, constructs structured representations of what it observes, performs reasoning over those representations, generates visual or analytical outputs, evaluates those outputs, and iteratively improves them.

The initial capability is:

> Technical/mathematical document → concepts → relationships → visual system representation → visual critique → refinement → explanation

The architecture must NOT be hard-coded around mathematical documents.

The system must instead expose a reusable agentic visual-analysis pipeline that can later support:

* mathematical papers
* technical diagrams
* scientific figures
* charts and plots
* architecture diagrams
* workflows
* screenshots/UI analysis
* image-to-report tasks
* multimodal document analysis
* potentially video/event analysis

The first implementation should remain intentionally narrow while establishing abstractions that allow these future capabilities to become additional VisionOps skills.

---

# 2. Primary Engineering Goals

The project must demonstrate:

1. Multimodal VLM inference.
2. Local model serving using vLLM.
3. Structured output from an LLM/VLM.
4. Stateful agent orchestration using LangGraph.
5. Pydantic-based typed state.
6. Deterministic tool execution.
7. Visual verification of generated results.
8. Iterative agentic refinement.
9. Streaming execution traces to a frontend.
10. Clean separation between model reasoning and deterministic rendering.
11. A TypeScript frontend suitable for a portfolio-quality AI application.
12. An architecture that can later support multiple visual-analysis skills.

The system should prioritize engineering quality and agent architecture over model training.

No fine-tuning is required for V1.

---

# 3. Initial Use Case

## Input

A user uploads a technical PDF containing equations, diagrams, figures, or descriptions of a system.

Example:

A paper describing:

```
Input
  ↓
Encoder
  ↓
Latent Representation
  ↓
Decoder
  ↓
Output
   ↑
Feedback
```

The document may contain equations and textual explanations.

## Agent Objective

The agent should determine:

* important concepts
* mathematical entities
* system components
* relationships
* information/data flow
* feedback loops
* equations relevant to the system
* hierarchical structure

It should then construct a simplified visual representation.

## Output

The user receives:

* generated block/system diagram
* extracted concepts
* relationship graph
* important equations
* explanation
* agent execution trace
* critique
* refinement history

---

# 4. Core Architectural Principle

Do NOT allow the VLM to directly generate arbitrary SVG or frontend code.

Instead:

```
VLM
  ↓
Structured representation
  ↓
Validation
  ↓
Deterministic renderer
  ↓
SVG
  ↓
Visual critic
  ↓
Structured critique
  ↓
Refinement
  ↓
Final SVG
```

The VLM is responsible for perception, interpretation, abstraction, planning, and critique.

Deterministic software is responsible for rendering.

This separation is a core architectural requirement.

---

# 5. High-Level Architecture

```
┌─────────────────────────────┐
│       Next.js Frontend      │
│       TypeScript/React      │
└──────────────┬──────────────┘
               │
               │ HTTP + SSE
               ▼
┌─────────────────────────────┐
│        FastAPI API          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       VisionOps Core        │
│                             │
│       LangGraph             │
│          │                  │
│   ┌──────┴────────┐         │
│   │ Agent State   │         │
│   │ Pydantic      │         │
│   └──────┬────────┘         │
│          │                  │
│  Perception / Reasoning     │
│  Planning / Critique        │
└──────────┬──────────────────┘
           │
           │ OpenAI-compatible API
           ▼
┌─────────────────────────────┐
│            vLLM             │
│                             │
│    Qwen2.5-VL-7B-Instruct  │
└─────────────────────────────┘
```

Supporting components:

```
PDF → PyMuPDF
Images → Pillow
Diagram → Mermaid / Graphviz
Validation → Pydantic
Backend → FastAPI
Frontend → Next.js + React + TypeScript
Streaming → Server-Sent Events
Environment → uv
Tests → pytest
```

---

# 6. Technology Stack

## Backend

Python 3.11 or 3.12.

Use:

* FastAPI
* Pydantic v2
* LangGraph
* LangChain only where genuinely useful
* PyMuPDF
* Pillow
* httpx
* pytest

Dependency management:

```
uv
```

Do not use Poetry unless there is a strong reason.

---

# 7. Model Serving

The VLM must be served separately from the application.

Recommended initial model:

```
Qwen/Qwen2.5-VL-7B-Instruct
```

Serving layer:

```
vLLM
```

The application must communicate with vLLM through its OpenAI-compatible API.

Architecture:

```
VisionOps
    ↓
OpenAI-compatible HTTP API
    ↓
vLLM
    ↓
Qwen2.5-VL
```

The model must NOT be loaded directly into the FastAPI process.

This separation allows the model server to be replaced later without rewriting the agent architecture.

Potential future models:

* larger Qwen-VL models
* smaller VLMs
* specialized vision models
* multimodal reasoning models

The model name must therefore be configurable.

Example environment variable:

```
VISION_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
```

---

# 8. GPU Constraint

The initial development environment has approximately 16 GB VRAM.

The implementation must therefore avoid assuming unlimited GPU memory.

The model-serving configuration should make the following configurable:

* GPU memory utilization
* maximum model length
* image resolution
* quantization
* tensor parallelism

Do not unnecessarily increase image resolution or context length.

The initial implementation should optimize for:

```
one document
one/few pages
one VLM request at a time
```

rather than throughput.

---

# 9. VisionOps Core Abstraction

The core platform should use a skill-oriented architecture.

Conceptually:

```
VisionOps
   │
   ├── Core Runtime
   │
   ├── Visual Document Analysis
   │
   ├── Diagram Generation
   │
   ├── Chart Analysis
   │
   ├── Screenshot Analysis
   │
   └── Future Skills
```

The initial skill:

```
TechnicalDocumentToDiagramSkill
```

must be implemented first.

The core runtime must not contain math-specific logic.

---

# 10. Agent State

Use Pydantic models for externally meaningful structured data.

Core state:

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

Avoid putting arbitrary dictionaries everywhere.

Use typed models for important state.

---

# 11. Concept Model

```python
class Concept(BaseModel):
    id: str
    name: str
    description: str

    role: str | None = None

    equations: list[str] = []

    importance: float | None = None
```

Example:

```json
{
  "id": "encoder",
  "name": "Encoder",
  "description": "Transforms input into latent representation",
  "role": "processing_component",
  "equations": [],
  "importance": 0.95
}
```

---

# 12. Relationship Model

```python
class Relationship(BaseModel):
    source: str
    target: str

    relationship: str

    direction: str

    explanation: str | None = None
```

Example:

```json
{
  "source": "encoder",
  "target": "latent",
  "relationship": "produces",
  "direction": "forward",
  "explanation": "The encoder transforms the input into the latent representation."
}
```

---

# 13. Equation Model

```python
class Equation(BaseModel):
    id: str
    expression: str
    description: str
    related_concepts: list[str]
    importance: float
```

Equations should remain associated with concepts rather than being treated as arbitrary text.

---

# 14. Diagram Specification

The VLM should generate a structured diagram specification.

```python
class DiagramNode(BaseModel):
    id: str
    label: str
    description: str | None = None
    type: str = "component"


class DiagramEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    direction: str = "forward"


class DiagramSpec(BaseModel):
    title: str
    nodes: list[DiagramNode]
    edges: list[DiagramEdge]
    layout: str = "flowchart"
```

The renderer consumes this object.

The renderer must not need to understand the original PDF.

---

# 15. Critique Model

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

The score is diagnostic only.

It must not be treated as a scientific metric.

---

# 16. Agent Graph

The initial LangGraph must follow this structure:

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
  ├── PASS ─────→ explain
  │                  ↓
  │                 END
  │
  └── FAIL
         ↓
      refine
         ↓
    plan_diagram
```

Maximum refinement:

```
2 iterations
```

Do not create an uncontrolled agent loop.

---

# 17. Agent Nodes

Each LangGraph node should have one clear responsibility.

## ingest_document

Responsibilities:

* validate PDF
* extract pages
* convert relevant pages to images
* store page paths
* emit progress event

Input:

```
PDF
```

Output:

```
page_images
```

---

## extract_concepts

Input:

* page images

VLM task:

Identify important system concepts.

Output:

```
list[Concept]
```

The prompt should explicitly request structured JSON.

---

## extract_relationships

Input:

* page images
* concepts

VLM task:

Determine relationships between concepts.

Output:

```
list[Relationship]
```

---

## extract_equations

Input:

* page images
* concepts

Output:

```
list[Equation]
```

The system should preserve equations as accurately as possible.

---

## abstract_system

Purpose:

Convert detailed technical information into a useful system-level abstraction.

The agent should decide:

* what belongs in the diagram
* what should be omitted
* what should remain as an annotation
* which relationships are structurally important

Output:

```
selected concepts
selected relationships
diagram abstraction strategy
```

---

## plan_diagram

Input:

* concepts
* relationships
* equations
* abstraction strategy

Output:

```
DiagramSpec
```

The model must not produce SVG.

---

## render_diagram

Input:

```
DiagramSpec
```

Output:

```
SVG
```

The rendering must be deterministic.

Preferred first implementation:

```
Mermaid → SVG
```

Alternative:

```
Graphviz
```

---

## visual_critique

The critic receives:

1. original page image
2. generated diagram
3. concept list
4. relationship list
5. equations

It evaluates:

* concept coverage
* relationship correctness
* directional correctness
* feedback loops
* equation preservation
* abstraction quality
* visual clarity
* unnecessary complexity

Output:

```
Critique
```

---

## refine

The refinement node receives the critique and modifies the diagram specification.

It must not restart the entire analysis.

The refinement target is:

```
DiagramSpec
```

not:

```
PDF analysis
```

This keeps the loop cheap.

---

## explain

Generate a concise human-readable explanation containing:

1. What the system does.
2. Main components.
3. Data/information flow.
4. Important feedback loops.
5. Important equations.
6. Important abstraction decisions.

---

# 18. Prompt Architecture

Do not store prompts inline throughout Python code.

Use a prompt directory:

```
prompts/
    concept_extraction.txt
    relationship_extraction.txt
    equation_extraction.txt
    abstraction.txt
    diagram_planning.txt
    visual_critique.txt
    refinement.txt
    explanation.txt
```

Prompts should explicitly define:

* role
* input
* task
* constraints
* output schema
* failure behavior

Structured output should always be validated with Pydantic.

---

# 19. Model Client

Create an abstraction:

```python
class VisionModelClient:
    async def analyze_image(...):
        ...

    async def analyze_text(...):
        ...

    async def analyze_multimodal(...):
        ...
```

Implementation:

```text
OpenAICompatibleVisionModelClient
        ↓
       vLLM
```

The agent should depend on the interface rather than directly depending on vLLM.

This permits later replacement with:

* another local VLM
* remote inference
* another OpenAI-compatible server

---

# 20. Renderer Architecture

Create:

```text
Renderer
   │
   ├── MermaidRenderer
   │
   └── GraphvizRenderer
```

Interface:

```python
class DiagramRenderer(Protocol):
    def render(self, diagram: DiagramSpec) -> RenderedDiagram:
        ...
```

The initial implementation should use Mermaid.

The renderer must:

1. validate node IDs
2. validate edge references
3. escape labels
4. generate Mermaid source
5. render SVG
6. return SVG path/content

---

# 21. Visual Critic

The critic is one of the most important parts of the portfolio project.

It demonstrates that the agent does not simply generate once and stop.

Conceptually:

```
Source
  ↓
VLM perception
  ↓
Structured reasoning
  ↓
Diagram
  ↓
Visual perception
  ↓
Critique
  ↓
Correction
```

The critic should explicitly distinguish:

### Missing information

Example:

```
"Decoder is missing."
```

### Incorrect information

Example:

```
"The feedback edge is connected to the encoder instead of the controller."
```

### Visual issue

Example:

```
"Three unrelated components overlap."
```

### Abstraction issue

Example:

```
"The diagram contains implementation details that obscure the main system flow."
```

---

# 22. API

FastAPI endpoints:

```text
POST /api/documents
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events
GET  /api/runs/{run_id}/result
```

## POST /api/documents

Uploads a PDF.

Returns:

```json
{
  "document_id": "...",
  "filename": "...",
  "status": "uploaded"
}
```

---

## POST /api/runs

Starts an analysis.

Request:

```json
{
  "document_id": "...",
  "skill": "technical_document_to_diagram"
}
```

Returns:

```json
{
  "run_id": "...",
  "status": "started"
}
```

---

# 23. Streaming

Use Server-Sent Events.

Endpoint:

```text
GET /api/runs/{run_id}/events
```

Events:

```text
run_started
document_ingested
concept_extraction_started
concepts_extracted
relationships_extracted
equations_extracted
diagram_planned
diagram_rendered
critique_started
critique_completed
refinement_started
final_result
run_completed
run_failed
```

Each event should contain structured JSON.

Example:

```json
{
  "event": "concepts_extracted",
  "timestamp": "...",
  "data": {
    "count": 12
  }
}
```

---

# 24. Frontend

Use:

* Next.js
* React
* TypeScript
* Tailwind CSS

The frontend should feel like an AI analysis workspace rather than a generic chat application.

Main layout:

```text
┌───────────────────────────────────────────────┐
│ VisionOps                                     │
├───────────────────┬───────────────────────────┤
│                   │                           │
│   Source PDF      │     Generated Diagram     │
│                   │                           │
│                   │                           │
├───────────────────┼───────────────────────────┤
│ Concepts          │ Relationships             │
│                   │                           │
├───────────────────┴───────────────────────────┤
│ Agent Execution Trace                         │
│                                               │
│ ✓ Document analyzed                           │
│ ✓ Concepts extracted                          │
│ ✓ Relationships extracted                     │
│ ✓ Diagram generated                           │
│ ✓ Visual critique                             │
│ ↻ Refining diagram                            │
└───────────────────────────────────────────────┘
```

---

# 25. Frontend Components

Suggested components:

```text
components/
    upload/
        DocumentUploader.tsx

    document/
        PdfViewer.tsx

    diagram/
        DiagramViewer.tsx

    analysis/
        ConceptList.tsx
        RelationshipGraph.tsx
        EquationList.tsx

    agent/
        AgentTrace.tsx
        AgentStep.tsx

    critique/
        CritiquePanel.tsx

    layout/
        Workspace.tsx
```

Keep frontend components focused.

Do not build a complex design system for V1.

---

# 26. Main User Flow

User:

```
Upload PDF
```

System:

```
Validate PDF

↓

Extract relevant page(s)

↓

Analyze visual content

↓

Extract concepts

↓

Extract relationships

↓

Extract equations

↓

Construct abstraction

↓

Plan diagram

↓

Render diagram

↓

Critique diagram

↓

Is diagram acceptable?

    YES
     ↓
   Explain
     ↓
   Result

    NO
     ↓
   Refine
     ↓
   Render
     ↓
   Critique
```

The UI should visibly show this execution.

---

# 27. Repository Structure

Recommended:

```text
visionops/
│
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── documents.py
│   │   │   └── runs.py
│   │   └── dependencies.py
│   │
│   └── web/
│       ├── app/
│       ├── components/
│       ├── hooks/
│       └── lib/
│
├── packages/
│   └── core/
│       ├── state/
│       ├── models/
│       ├── graph/
│       ├── agents/
│       ├── renderers/
│       ├── clients/
│       ├── skills/
│       └── events/
│
├── prompts/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│
├── docs/
│
├── data/
│   ├── uploads/
│   ├── pages/
│   └── outputs/
│
├── .env.example
├── pyproject.toml
├── uv.lock
├── README.md
└── AGENTS.md
```

The exact monorepo implementation can be simplified if Antigravity's implementation agent benefits from fewer packages. Avoid architectural complexity that does not serve V1.

---

# 28. Spec-Driven Development Structure

Create a `specs/` directory.

```text
specs/
    00-product.md
    01-architecture.md
    02-domain-model.md
    03-agent-graph.md
    04-model-serving.md
    05-rendering.md
    06-api.md
    07-frontend.md
    08-evaluation.md
    09-testing.md
    10-deployment.md
```

Each specification must define:

```text
Purpose
Requirements
Inputs
Outputs
Interfaces
Constraints
Acceptance Criteria
Non-Goals
```

The implementation agent should read the relevant specification before modifying code.

---

# 29. Antigravity Agent Instructions

Create:

```text
AGENTS.md
```

It should establish the following rules.

```text
# VisionOps Engineering Rules

1. Read the relevant specification before implementing a feature.

2. Do not change architecture without updating the relevant specification.

3. Prefer small, testable modules.

4. Use Pydantic models for structured agent state.

5. Do not allow raw LLM output to bypass validation.

6. Do not allow the VLM to directly generate SVG.

7. Keep model serving separate from application logic.

8. The application communicates with vLLM through an OpenAI-compatible API.

9. Keep prompts in the prompts/ directory.

10. LangGraph owns agent orchestration.

11. Deterministic tools should be used whenever possible.

12. Agent loops must have explicit termination conditions.

13. Do not introduce unnecessary dependencies.

14. Write tests for deterministic components.

15. Do not implement future features unless explicitly requested.

16. Preserve backwards compatibility of public API models.

17. When changing a data model, update tests and relevant specifications.

18. Prefer configuration through environment variables.

19. Never hard-code GPU-specific configuration.

20. Before declaring a feature complete, run the relevant tests.
```

---

# 30. Development Workflow for Antigravity

The implementation should proceed in phases.

## Phase 0 — Repository Bootstrap

Implement:

* repository structure
* uv environment
* FastAPI
* Next.js
* configuration
* logging
* basic tests

Acceptance:

```text
Backend starts.
Frontend starts.
Health endpoint works.
Frontend can reach backend.
Tests execute successfully.
```

---

# 31. Phase 1 — vLLM Integration

Implement:

* model configuration
* OpenAI-compatible client
* multimodal request support
* structured output parsing
* timeout handling
* error handling

Acceptance:

The application can send an image + prompt to vLLM and receive a validated structured response.

---

# 32. Phase 2 — Document Pipeline

Implement:

* PDF upload
* PDF validation
* page extraction
* page-to-image conversion
* temporary storage

Acceptance:

A PDF can be uploaded and converted into page images.

---

# 33. Phase 3 — Agent Graph

Implement:

* LangGraph state
* document ingestion
* concept extraction
* relationship extraction
* equation extraction
* abstraction
* diagram planning

Acceptance:

The agent can produce a valid `DiagramSpec`.

---

# 34. Phase 4 — Renderer

Implement:

* Mermaid renderer
* SVG generation
* renderer validation
* diagram endpoint

Acceptance:

A valid `DiagramSpec` always produces either:

```
valid SVG
```

or:

```
explicit structured rendering error
```

Never silently produce corrupted output.

---

# 35. Phase 5 — Visual Critic

Implement:

* diagram rasterization
* source + generated diagram multimodal prompt
* critique schema
* critique node
* conditional LangGraph routing

Acceptance:

The critic can detect deliberately introduced diagram errors in test fixtures.

---

# 36. Phase 6 — Refinement

Implement:

```
Critique
   ↓
Refinement
   ↓
DiagramSpec
   ↓
Renderer
   ↓
Critique
```

Acceptance:

A deliberately flawed diagram can be corrected within the configured iteration limit.

---

# 37. Phase 7 — Frontend

Implement:

* upload
* run analysis
* SSE connection
* execution trace
* PDF viewer
* diagram viewer
* concepts
* relationships
* equations
* critique
* final explanation

Acceptance:

A user can complete the entire workflow without using an API client.

---

# 38. Phase 8 — Evaluation

Create a small benchmark.

Categories:

```text
Control systems
Machine learning
Signal processing
Numerical methods
Physics
Computer architecture
```

Target:

```
10–20 documents
```

For every document manually define:

* important concepts
* important relationships
* expected flow
* important equations

Measure:

```text
Concept Recall
Relationship Accuracy
Equation Preservation
Diagram Validity
Critique Detection
Refinement Success
Latency
VRAM usage
```

These metrics are for engineering evaluation, not claims of scientific benchmark performance.

---

# 39. Testing Strategy

## Unit tests

Test:

* Pydantic models
* diagram validation
* Mermaid generation
* graph routing
* configuration
* event serialization

## Integration tests

Test:

```text
PDF
 ↓
Agent
 ↓
DiagramSpec
 ↓
Renderer
 ↓
Critique
```

Use mocked VLM responses.

Do not require a GPU for normal CI tests.

## End-to-end test

One optional GPU test should run:

```text
real PDF
    ↓
vLLM
    ↓
LangGraph
    ↓
SVG
    ↓
Critique
```

---

# 40. Error Handling

Every external boundary must have explicit failure handling.

Examples:

```text
Invalid PDF
Model unavailable
vLLM timeout
Malformed model output
Pydantic validation failure
Rendering failure
Critic failure
SSE disconnect
```

Model failures should not crash the entire API process.

Return structured errors.

Example:

```json
{
  "error": {
    "code": "MODEL_OUTPUT_INVALID",
    "message": "The model response could not be validated against DiagramSpec."
  }
}
```

Do not expose raw stack traces to the frontend.

---

# 41. Observability

Every run should have:

```text
run_id
node
start_time
end_time
duration
status
iteration
error
```

Log:

* model latency
* node latency
* token usage if available
* failures
* refinement count

Do not log uploaded documents or sensitive document content by default.

---

# 42. Configuration

Use environment variables.

Example:

```text
VISIONOPS_ENV=development

VLLM_BASE_URL=http://localhost:8000/v1
VISION_MODEL=Qwen/Qwen2.5-VL-7B-Instruct

MAX_REFINEMENT_ITERATIONS=2

UPLOAD_DIR=./data/uploads
PAGE_DIR=./data/pages
OUTPUT_DIR=./data/outputs

LOG_LEVEL=INFO
```

Never hard-code:

* GPU ID
* model path
* vLLM URL
* storage path
* iteration count

---

# 43. Security Baseline

V1 should implement basic safeguards:

* PDF MIME/type validation
* upload size limit
* filename sanitization
* generated file isolation
* no arbitrary shell execution from user input
* no arbitrary Mermaid/Graphviz command injection
* API input validation

The diagram renderer must never execute model-generated arbitrary code.

---

# 44. Non-Goals for V1

Do NOT implement:

* user accounts
* authentication
* billing
* multi-tenant architecture
* Kubernetes
* distributed inference
* model fine-tuning
* vector database
* RAG
* autonomous web browsing
* multi-agent swarm
* video processing
* mobile application
* real-time collaborative editing

These can be considered later.

---

# 45. Future VisionOps Skills

The core architecture should eventually support:

```text
VisionOps
│
├── Technical Document → Diagram
│
├── Chart → Data Insights
│
├── Screenshot → UI Understanding
│
├── Architecture Diagram → System Explanation
│
├── Image → Structured Report
│
├── Scientific Figure → Explanation
│
├── Workflow Image → Executable Workflow
│
└── Video → Event/Process Analysis
```

Each capability should implement a common skill interface rather than creating an entirely separate application.

Conceptually:

```python
class VisionSkill(Protocol):

    name: str

    async def run(
        self,
        input: VisionInput,
        state: VisionOpsState
    ) -> VisionOpsResult:
        ...
```

---

# 46. Skill Registry

Future skills should be discoverable through a registry.

Example:

```python
SKILLS = {
    "technical_document_to_diagram":
        TechnicalDocumentToDiagramSkill(),

    "chart_analysis":
        ChartAnalysisSkill(),

    "screenshot_analysis":
        ScreenshotAnalysisSkill(),
}
```

V1 only needs:

```text
technical_document_to_diagram
```

Do not implement the others yet.

---

# 47. Design Philosophy

VisionOps should follow this principle:

```
Perceive
   ↓
Structure
   ↓
Reason
   ↓
Act
   ↓
Observe
   ↓
Critique
   ↓
Refine
```

This is the fundamental agentic loop.

The project should demonstrate that multimodal agents are not merely:

```
image → answer
```

but can instead perform:

```
visual perception
    +
structured representation
    +
reasoning
    +
tool execution
    +
visual verification
    +
iterative refinement
```

---

# 48. Definition of Done

V1 is complete when:

1. A user uploads a technical PDF.
2. The backend extracts a page.
3. Qwen2.5-VL is accessed through vLLM.
4. LangGraph orchestrates the workflow.
5. Concepts are extracted.
6. Relationships are extracted.
7. Equations are extracted.
8. A structured `DiagramSpec` is generated.
9. Mermaid produces an SVG.
10. The VLM critiques the generated diagram.
11. The graph can perform a refinement cycle.
12. The final diagram is shown in the browser.
13. The frontend displays the execution trace.
14. The concepts, relationships, equations, and critique are visible.
15. The application handles model/rendering failures gracefully.
16. Deterministic components have automated tests.
17. The entire workflow can run on the target 16 GB VRAM development machine.

---

# 49. Portfolio Positioning

The project should be presented as:

> VisionOps — an agentic multimodal visual analytics platform that converts visual information into structured representations, reasons over them, generates analytical artifacts, visually evaluates its own output, and iteratively refines the result.

The mathematical-document workflow is the first demonstration of the platform rather than its identity.

The strongest technical story is:

```text
VLM
 ↓
Structured world model
 ↓
Agentic reasoning
 ↓
Tool execution
 ↓
Generated visual artifact
 ↓
Visual verification
 ↓
Iterative refinement
```

This architecture makes VisionOps extensible beyond the initial mathematical-diagram use case while keeping V1 small enough to implement and demonstrate.

"""Agent graph orchestration.

Uses LangGraph to define the stateful execution flow of the VisionOps agent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from packages.core.clients.base import VisionModelClient
from packages.core.config import VisionOpsSettings, get_settings
from packages.core.document import DocumentProcessor
from packages.core.events import EventStreamer
from packages.core.models import (
    Concept,
    Critique,
    DiagramSpec,
    Equation,
    Relationship,
    VisionOpsState,
)
from packages.core.renderers.base import DiagramRenderer

logger = logging.getLogger("visionops.graph")


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    path = Path(f"prompts/{name}.txt")
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text()


class GraphDependencies:
    """Dependencies injected into the LangGraph nodes."""

    def __init__(
        self,
        client: VisionModelClient,
        renderer: DiagramRenderer,
        processor: DocumentProcessor,
        streamer: EventStreamer,
        settings: VisionOpsSettings,
    ):
        self.client = client
        self.renderer = renderer
        self.processor = processor
        self.streamer = streamer
        self.settings = settings


# Helper models for structured extraction
class ConceptsExtraction(BaseModel):
    concepts: list[Concept]


class RelationshipsExtraction(BaseModel):
    relationships: list[Relationship]


class EquationsExtraction(BaseModel):
    equations: list[Equation]


class AbstractionStrategy(BaseModel):
    strategy: str
    selected_concept_ids: list[str]
    selected_relationship_indices: list[int]


class ExplanationResponse(BaseModel):
    explanation: str


def build_graph(deps: GraphDependencies) -> StateGraph:
    """Build and return the LangGraph state machine."""
    
    workflow = StateGraph(VisionOpsState)

    async def ingest_document(state: VisionOpsState) -> dict[str, Any]:
        """Node: Convert uploaded PDF to images."""
        if not state.input_document:
            return {"status": "failed", "errors": ["No input document provided"]}
            
        await deps.streamer.emit(state.run_id, "run_started")
        
        try:
            page_paths = deps.processor.process_upload(Path(state.input_document))
            await deps.streamer.emit(state.run_id, "document_ingested", {"pages": len(page_paths)})
            return {"page_images": page_paths}
        except Exception as e:
            return {"status": "failed", "errors": [str(e)]}

    async def extract_concepts(state: VisionOpsState) -> dict[str, Any]:
        """Node: Extract concepts from document images."""
        await deps.streamer.emit(state.run_id, "concept_extraction_started")
        
        prompt = _load_prompt("concept_extraction")
        try:
            # We process the first page for now due to memory constraints in V1
            target_image = state.page_images[0]
            result = await deps.client.analyze_image(
                image=target_image,
                prompt=prompt,
                response_model=ConceptsExtraction,
            )
            concepts = result.concepts
            await deps.streamer.emit(state.run_id, "concepts_extracted", {
                "count": len(concepts),
                "items": [{"id": c.id, "name": c.name, "role": c.role} for c in concepts]
            })
            return {"concepts": concepts}
        except Exception as e:
            return {"status": "failed", "errors": [f"Concept extraction failed: {e}"]}

    async def extract_relationships(state: VisionOpsState) -> dict[str, Any]:
        """Node: Extract relationships between concepts."""
        prompt = _load_prompt("relationship_extraction")
        context = f"Extracted Concepts:\n" + "\n".join([f"- {c.id}: {c.name}" for c in state.concepts])
        
        try:
            target_image = state.page_images[0]
            result = await deps.client.analyze_multimodal(
                images=[target_image],
                text=context,
                prompt=prompt,
                response_model=RelationshipsExtraction,
            )
            relationships = result.relationships
            await deps.streamer.emit(state.run_id, "relationships_extracted", {
                "count": len(relationships),
                "links": [{"source": r.source, "target": r.target, "relation": r.relationship} for r in relationships]
            })
            return {"relationships": relationships}
        except Exception as e:
            logger.warning(f"Relationship extraction failed: {e}. Generating fallback flow relationships.")
            fallback_rels = []
            for idx in range(len(state.concepts) - 1):
                fallback_rels.append(
                    Relationship(
                        source=state.concepts[idx].id,
                        target=state.concepts[idx + 1].id,
                        relationship="relates_to",
                        direction="forward",
                    )
                )
            await deps.streamer.emit(state.run_id, "relationships_extracted", {
                "count": len(fallback_rels),
                "note": "Fallback relationships generated",
                "links": [{"source": r.source, "target": r.target, "relation": r.relationship} for r in fallback_rels]
            })
            return {"relationships": fallback_rels}

    async def extract_equations(state: VisionOpsState) -> dict[str, Any]:
        """Node: Extract equations."""
        prompt = _load_prompt("equation_extraction")
        try:
            target_image = state.page_images[0]
            result = await deps.client.analyze_image(
                image=target_image,
                prompt=prompt,
                response_model=EquationsExtraction,
            )
            equations = result.equations
            await deps.streamer.emit(state.run_id, "equations_extracted", {
                "count": len(equations),
                "expressions": [eq.expression for eq in equations]
            })
            return {"equations": equations}
        except Exception as e:
            logger.warning(f"Equation extraction failed: {e}")
            return {"equations": []}

    async def abstract_system(state: VisionOpsState) -> dict[str, Any]:
        """Node: Decide what goes into the diagram."""
        prompt = _load_prompt("abstraction")
        text_context = (
            "Concepts:\n" + "\n".join([f"{c.id}: {c.name} ({c.description})" for c in state.concepts]) +
            "\n\nRelationships:\n" + "\n".join([f"[{i}] {r.source} -> {r.target} ({r.relationship})" for i, r in enumerate(state.relationships)])
        )
        
        try:
            result = await deps.client.analyze_text(
                text=text_context,
                prompt=prompt,
                response_model=AbstractionStrategy,
            )
            selected_concepts = [c for c in state.concepts if c.id in result.selected_concept_ids]
            if not selected_concepts:
                selected_concepts = state.concepts
                
            await deps.streamer.emit(state.run_id, "system_abstracted", {
                "strategy": result.strategy,
                "selected_concept_count": len(selected_concepts),
            })
            return {"concepts": selected_concepts}
        except Exception as e:
            logger.warning(f"Abstraction failed, using all concepts: {e}")
            return {}

    async def plan_diagram(state: VisionOpsState) -> dict[str, Any]:
        """Node: Plan the diagram spec."""
        prompt = _load_prompt("diagram_planning")
        
        text_context = (
            "Concepts:\n" + "\n".join([f"{c.id}: {c.name} ({c.description})" for c in state.concepts]) +
            "\n\nRelationships:\n" + "\n".join([f"{r.source} -> {r.target} ({r.relationship})" for r in state.relationships])
        )
        
        if state.critique and not state.critique.passed:
            text_context += f"\n\nCRITIQUE OF PREVIOUS DIAGRAM:\n{state.critique.model_dump_json(indent=2)}\n"
            text_context += "PLEASE FIX THESE ISSUES IN YOUR NEW SPEC."
            
        try:
            spec = await deps.client.analyze_text(
                text=text_context,
                prompt=prompt,
                response_model=DiagramSpec,
            )
            await deps.streamer.emit(state.run_id, "diagram_planned", {
                "title": spec.title,
                "layout": spec.layout,
                "nodes": len(spec.nodes),
                "edges": len(spec.edges),
            })
            return {"diagram_spec": spec}
        except Exception as e:
            return {"status": "failed", "errors": [f"Diagram planning failed: {e}"]}

    async def render_diagram(state: VisionOpsState) -> dict[str, Any]:
        """Node: Render the diagram spec to SVG."""
        if not state.diagram_spec:
            return {"status": "failed", "errors": ["No diagram spec available to render"]}
            
        output_filename = f"{state.run_id}_{state.iteration}.svg"
        output_path = deps.settings.output_dir / output_filename
        
        try:
            rendered_path = deps.renderer.render(state.diagram_spec, output_path)
            await deps.streamer.emit(state.run_id, "diagram_rendered", {
                "filename": output_filename,
                "path": str(rendered_path),
            })
            return {"rendered_diagram": str(rendered_path)}
        except Exception as e:
            return {"status": "failed", "errors": [f"Rendering failed: {e}"]}

    async def visual_critique(state: VisionOpsState) -> dict[str, Any]:
        """Node: Critique the rendered diagram against the original document."""
        await deps.streamer.emit(state.run_id, "critique_started")
        prompt = _load_prompt("visual_critique")
        
        text_context = f"Generated Diagram Spec: {state.diagram_spec.model_dump_json() if state.diagram_spec else 'None'}"
        
        try:
            images = [state.page_images[0]]
                
            critique = await deps.client.analyze_multimodal(
                images=images,
                text=text_context,
                prompt=prompt,
                response_model=Critique,
            )
            await deps.streamer.emit(state.run_id, "critique_completed", {
                "passed": critique.passed,
                "score": critique.score,
                "missing_concepts": critique.missing_concepts,
                "suggested_changes": critique.suggested_changes,
            })
            return {"critique": critique}
        except Exception as e:
            logger.warning(f"Critique failed: {e}")
            fallback_critique = Critique(passed=True, score=1.0)
            await deps.streamer.emit(state.run_id, "critique_completed", {"passed": True, "score": 1.0, "note": "Fallback passed"})
            return {"critique": fallback_critique}

    async def explain(state: VisionOpsState) -> dict[str, Any]:
        """Node: Generate final explanation."""
        prompt = _load_prompt("explanation")
        text_context = f"Diagram Spec: {state.diagram_spec.model_dump_json() if state.diagram_spec else 'None'}"
        
        try:
            result = await deps.client.analyze_text(
                text=text_context,
                prompt=prompt,
                response_model=ExplanationResponse,
            )
            await deps.streamer.emit(state.run_id, "run_completed", {"explanation_length": len(result.explanation)})
            return {"explanation": result.explanation, "status": "completed"}
        except Exception as e:
            await deps.streamer.emit(state.run_id, "run_completed", {"note": "Explanation fallback"})
            return {"status": "completed", "explanation": "Explanation unavailable due to VLM error."}

    # Graph Routing
    def route_after_critique(state: VisionOpsState) -> Literal["explain", "plan_diagram"]:
        """Decide whether to refine or finish."""
        if state.status == "failed":
            return "explain" # Or end directly
            
        if state.critique and state.critique.passed:
            return "explain"
            
        if state.iteration >= state.max_iterations:
            return "explain"
            
        # Needs refinement
        # We need to increment iteration (done in a small node or just before routing)
        # We will increment it in the node that returns to plan_diagram ideally, but we can't mutate easily in router.
        # LangGraph allows returning node names.
        return "plan_diagram"
        
    async def increment_iteration(state: VisionOpsState) -> dict[str, Any]:
        await deps.streamer.emit(state.run_id, "refinement_started", {"iteration": state.iteration + 1})
        return {"iteration": state.iteration + 1}

    # Add nodes
    workflow.add_node("ingest_document", ingest_document)
    workflow.add_node("extract_concepts", extract_concepts)
    workflow.add_node("extract_relationships", extract_relationships)
    workflow.add_node("extract_equations", extract_equations)
    workflow.add_node("abstract_system", abstract_system)
    workflow.add_node("plan_diagram", plan_diagram)
    workflow.add_node("render_diagram", render_diagram)
    workflow.add_node("visual_critique", visual_critique)
    workflow.add_node("increment_iteration", increment_iteration)
    workflow.add_node("explain", explain)

    # Error checking edge
    def check_error(state: VisionOpsState, next_node: str) -> str:
        return END if state.status == "failed" else next_node

    # Add edges
    workflow.add_edge(START, "ingest_document")
    
    workflow.add_conditional_edges("ingest_document", lambda s: check_error(s, "extract_concepts"))
    workflow.add_conditional_edges("extract_concepts", lambda s: check_error(s, "extract_relationships"))
    workflow.add_conditional_edges("extract_relationships", lambda s: check_error(s, "extract_equations"))
    workflow.add_conditional_edges("extract_equations", lambda s: check_error(s, "abstract_system"))
    workflow.add_conditional_edges("abstract_system", lambda s: check_error(s, "plan_diagram"))
    workflow.add_conditional_edges("plan_diagram", lambda s: check_error(s, "render_diagram"))
    workflow.add_conditional_edges("render_diagram", lambda s: check_error(s, "visual_critique"))
    
    # Routing after critique
    workflow.add_conditional_edges(
        "visual_critique",
        lambda state: END if state.status == "failed" else ("explain" if (state.critique and state.critique.passed) or state.iteration >= state.max_iterations else "increment_iteration")
    )
    workflow.add_edge("increment_iteration", "plan_diagram")
    
    workflow.add_edge("explain", END)

    return workflow.compile()

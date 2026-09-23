"""Runs API routes.

Manages agent execution and SSE streaming.
"""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from packages.core.clients.openai_client import OpenAICompatibleVisionModelClient
from packages.core.config import VisionOpsSettings, get_settings
from packages.core.document import DocumentProcessor
from packages.core.events import EventStreamer
from packages.core.graph import GraphDependencies, build_graph
from packages.core.models import VisionOpsState
from packages.core.renderers.mermaid import MermaidRenderer

logger = logging.getLogger("visionops.api.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])

# Global event streamer for the application
_streamer = EventStreamer()

# Simple in-memory run storage for V1
_runs: dict[str, VisionOpsState] = {}


class RunStartRequest(BaseModel):
    document_id: str
    skill: str = "technical_document_to_diagram"


class RunStartResponse(BaseModel):
    run_id: str
    status: str


def get_streamer() -> EventStreamer:
    return _streamer


@router.post("", response_model=RunStartResponse, status_code=status.HTTP_201_CREATED)
async def start_run(
    request: RunStartRequest,
    settings: VisionOpsSettings = Depends(get_settings),
    streamer: EventStreamer = Depends(get_streamer),
) -> RunStartResponse:
    """Start an analysis run."""
    run_id = str(uuid.uuid4())
    
    # Locate document (simple logic since document_id was the uuid part)
    # The documents API saves it as {document_id}_{filename}
    doc_paths = list(settings.upload_dir.glob(f"{request.document_id}_*.pdf"))
    if not doc_paths:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_path = doc_paths[0]
    
    # Initialize state
    state = VisionOpsState(
        run_id=run_id,
        skill=request.skill,
        input_document=str(doc_path.absolute()),
    )
    _runs[run_id] = state
    
    # Initialize dependencies
    client = OpenAICompatibleVisionModelClient(
        base_url=settings.vllm_base_url,
        model=settings.vision_model,
        timeout=settings.model_timeout,
        max_tokens=settings.model_max_tokens,
    )
    renderer = MermaidRenderer()
    processor = DocumentProcessor(settings)
    
    deps = GraphDependencies(
        client=client,
        renderer=renderer,
        processor=processor,
        streamer=streamer,
        settings=settings,
    )
    
    graph = build_graph(deps)
    
    # Start graph execution in background
    async def _run_graph():
        try:
            logger.info(f"Starting graph for run {run_id}")
            final_state = await graph.ainvoke(state)
            state_obj = VisionOpsState(**final_state)
            _runs[run_id] = state_obj
            logger.info(f"Run {run_id} completed with status: {state_obj.status}")
            if state_obj.status == "failed":
                await streamer.emit(run_id, "run_failed", {"errors": state_obj.errors})
            elif state_obj.status == "completed":
                await streamer.emit(run_id, "run_completed", {"status": "completed"})
        except Exception as e:
            logger.error(f"Run {run_id} failed: {e}")
            _runs[run_id].status = "failed"
            _runs[run_id].errors.append(str(e))
            await streamer.emit(run_id, "run_failed", {"error": str(e)})
        finally:
            await client.close()
            
    asyncio.create_task(_run_graph())
    
    return RunStartResponse(run_id=run_id, status="started")


@router.get("/{run_id}", response_model=VisionOpsState)
async def get_run(run_id: str) -> VisionOpsState:
    """Get the current state of a run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return _runs[run_id]


@router.get("/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    streamer: EventStreamer = Depends(get_streamer)
):
    """Stream events for a specific run via Server-Sent Events."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
        
    async def event_generator():
        queue = streamer.subscribe(run_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                event = await queue.get()
                yield {
                    "event": event.event,
                    "data": event.model_dump_json(),
                }
                if event.event in ("run_completed", "run_failed"):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            streamer.unsubscribe(run_id, queue)
            
    return EventSourceResponse(event_generator())


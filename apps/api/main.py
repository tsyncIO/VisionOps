"""VisionOps FastAPI application entry point.

This is the main FastAPI application that serves as the API layer
between the Next.js frontend and the VisionOps core.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.core.config import get_settings
from apps.api.routes import documents, health


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("visionops")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan — startup and shutdown."""
        logger.info("VisionOps API starting up")
        settings.ensure_directories()
        logger.info(f"Environment: {settings.visionops_env}")
        logger.info(f"vLLM endpoint: {settings.vllm_base_url}")
        logger.info(f"Model: {settings.vision_model}")
        yield
        logger.info("VisionOps API shutting down")

    app = FastAPI(
        title="VisionOps API",
        description="Agentic Multimodal Visual Analytics & Reasoning Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(health.router, prefix="/api")
    app.include_router(documents.router)

    return app


# Create the application instance
app = create_app()

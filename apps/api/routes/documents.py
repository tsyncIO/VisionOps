"""Document API routes."""

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from packages.core.config import VisionOpsSettings, get_settings

logger = logging.getLogger("visionops.api.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    settings: VisionOpsSettings = Depends(get_settings),
) -> DocumentUploadResponse:
    """Upload a PDF document for analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    # Read first few bytes to verify it's a PDF
    header = await file.read(5)
    await file.seek(0)
    if header != b"%PDF-":
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}_{file.filename}"
    file_path = settings.upload_dir / safe_filename
    
    settings.ensure_directories()

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Check file size (optional based on setting)
        file_size = file_path.stat().st_size
        if file_size > settings.max_upload_size_bytes:
            file_path.unlink()
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB"
            )
            
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail="Failed to save file")

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="uploaded"
    )

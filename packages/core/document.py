"""Document processing pipeline.

Handles PDF validation, extraction, and rendering pages to images
for consumption by the VLM.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from packages.core.config import VisionOpsSettings, get_settings

logger = logging.getLogger("visionops.document")


class DocumentProcessorError(Exception):
    """Base error for document processing."""
    pass


def validate_pdf(file_path: Path) -> None:
    """Validate that a file is a valid PDF."""
    if not file_path.exists():
        raise DocumentProcessorError(f"File not found: {file_path}")
    
    try:
        # Just try to open it; PyMuPDF will raise an error if invalid
        with fitz.open(str(file_path)) as doc:
            if not doc.is_pdf:
                raise DocumentProcessorError(f"File is not a PDF: {file_path}")
            if doc.page_count == 0:
                raise DocumentProcessorError(f"PDF has no pages: {file_path}")
    except Exception as e:
        raise DocumentProcessorError(f"Invalid PDF: {e}")


def extract_page_images(
    file_path: Path,
    output_dir: Path,
    dpi: int = 150,
    page_numbers: list[int] | None = None,
) -> list[str]:
    """Extract pages from a PDF and save them as PNG images.

    Args:
        file_path: Path to the PDF file.
        output_dir: Directory to save the extracted images.
        dpi: Resolution for the extracted images. 150 is usually sufficient
             for the VLM while keeping VRAM usage reasonable.
        page_numbers: Optional list of 0-indexed page numbers to extract.
                      If None, extracts all pages.

    Returns:
        List of absolute paths to the saved PNG files.
    """
    validate_pdf(file_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved_paths: list[str] = []
    
    try:
        with fitz.open(str(file_path)) as doc:
            pages_to_process = page_numbers if page_numbers is not None else list(range(doc.page_count))
            
            for page_num in pages_to_process:
                if page_num < 0 or page_num >= doc.page_count:
                    logger.warning(f"Skipping invalid page number {page_num}")
                    continue
                    
                page = doc.load_page(page_num)
                # zoom factor for DPI (PyMuPDF default is 72)
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image for standardized saving
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                output_filename = f"{file_path.stem}_page_{page_num + 1}.png"
                output_path = output_dir / output_filename
                
                img.save(output_path, format="PNG", optimize=True)
                saved_paths.append(str(output_path.absolute()))
                logger.debug(f"Saved page {page_num + 1} to {output_path}")
                
    except Exception as e:
        raise DocumentProcessorError(f"Failed to extract pages: {e}")
        
    return saved_paths


class DocumentProcessor:
    """Service for handling document ingestion."""
    
    def __init__(self, settings: VisionOpsSettings | None = None):
        self.settings = settings or get_settings()
        
    def process_upload(self, file_path: Path, page_numbers: list[int] | None = None) -> list[str]:
        """Process an uploaded PDF and return paths to the extracted page images.
        
        This will be called by the first node in the agent graph.
        """
        logger.info(f"Processing document: {file_path}")
        return extract_page_images(
            file_path=file_path,
            output_dir=self.settings.page_dir,
            page_numbers=page_numbers,
        )

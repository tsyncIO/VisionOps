"""Unit tests for the document processor."""

import tempfile
from pathlib import Path

import fitz
import pytest
from PIL import Image

from packages.core.config import VisionOpsSettings
from packages.core.document import (
    DocumentProcessor,
    DocumentProcessorError,
    extract_page_images,
    validate_pdf,
)


def create_dummy_pdf(path: Path) -> None:
    """Create a minimal valid PDF with 2 pages for testing."""
    doc = fitz.open()
    doc.new_page(width=100, height=100)
    doc.new_page(width=100, height=100)
    doc.save(str(path))
    doc.close()


class TestDocumentProcessor:
    @pytest.fixture
    def temp_dirs(self):
        with tempfile.TemporaryDirectory() as upload_dir, tempfile.TemporaryDirectory() as page_dir:
            yield Path(upload_dir), Path(page_dir)

    @pytest.fixture
    def dummy_pdf(self, temp_dirs):
        upload_dir, _ = temp_dirs
        pdf_path = upload_dir / "test.pdf"
        create_dummy_pdf(pdf_path)
        return pdf_path

    def test_validate_pdf_valid(self, dummy_pdf):
        validate_pdf(dummy_pdf)  # Should not raise

    def test_validate_pdf_not_found(self):
        with pytest.raises(DocumentProcessorError, match="File not found"):
            validate_pdf(Path("/nonexistent/file.pdf"))

    def test_validate_pdf_invalid_format(self, temp_dirs):
        upload_dir, _ = temp_dirs
        invalid_path = upload_dir / "invalid.pdf"
        invalid_path.write_bytes(b"not a pdf")
        
        with pytest.raises(DocumentProcessorError, match="Invalid PDF"):
            validate_pdf(invalid_path)

    def test_extract_page_images_all(self, dummy_pdf, temp_dirs):
        _, page_dir = temp_dirs
        paths = extract_page_images(dummy_pdf, page_dir)
        
        assert len(paths) == 2
        for path in paths:
            assert Path(path).exists()
            assert path.endswith(".png")
            # Verify it's a valid image
            with Image.open(path) as img:
                assert img.format == "PNG"

    def test_extract_page_images_specific_pages(self, dummy_pdf, temp_dirs):
        _, page_dir = temp_dirs
        # Only extract the second page (index 1)
        paths = extract_page_images(dummy_pdf, page_dir, page_numbers=[1])
        
        assert len(paths) == 1
        assert "page_2.png" in paths[0]
        assert Path(paths[0]).exists()

    def test_processor_service(self, dummy_pdf, temp_dirs):
        upload_dir, page_dir = temp_dirs
        settings = VisionOpsSettings(
            upload_dir=upload_dir,
            page_dir=page_dir,
            output_dir=upload_dir
        )
        processor = DocumentProcessor(settings=settings)
        
        paths = processor.process_upload(dummy_pdf)
        assert len(paths) == 2

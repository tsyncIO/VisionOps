"""Unit tests for the documents API."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.core.config import VisionOpsSettings, get_settings


def test_upload_document_success(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    
    def mock_get_settings():
        settings = VisionOpsSettings(
            upload_dir=upload_dir,
            page_dir=tmp_path / "pages",
            output_dir=tmp_path / "outputs"
        )
        return settings
        
    app.dependency_overrides[get_settings] = mock_get_settings
    
    client = TestClient(app)
    
    # Create fake PDF content
    pdf_content = b"%PDF-1.4\n%Fake PDF content for testing\n"
    
    response = client.post(
        "/api/documents",
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "test.pdf"
    assert data["status"] == "uploaded"
    
    # Verify file was saved
    saved_files = list(upload_dir.glob("*.pdf"))
    assert len(saved_files) == 1
    assert saved_files[0].name.endswith("test.pdf")
    assert saved_files[0].read_bytes() == pdf_content
    
    # cleanup
    app.dependency_overrides.clear()


def test_upload_document_invalid_extension():
    client = TestClient(app)
    
    response = client.post(
        "/api/documents",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}
    )
    
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_document_invalid_content():
    client = TestClient(app)
    
    response = client.post(
        "/api/documents",
        files={"file": ("test.pdf", io.BytesIO(b"not a pdf content"), "application/pdf")}
    )
    
    assert response.status_code == 400
    assert "Invalid PDF file" in response.json()["detail"]

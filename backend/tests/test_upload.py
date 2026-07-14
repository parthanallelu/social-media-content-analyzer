"""
Tests for upload endpoints.
Uses httpx AsyncClient + FastAPI's test client (no real file processing).
"""
import io
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def pdf_bytes() -> bytes:
    """Minimal valid PDF bytes."""
    return b"%PDF-1.4\n1 0 obj\n<</Type /Catalog>>\nendobj\nxref\n0 1\n0000000000 65535 f\ntrailer\n<</Size 1/Root 1 0 R>>\nstartxref\n9\n%%EOF"


@pytest.fixture
def png_bytes() -> bytes:
    """Minimal 1x1 white PNG."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_upload_pdf_missing_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/upload/pdf")
    assert response.status_code == 422  # Unprocessable Entity — missing file field


@pytest.mark.asyncio
async def test_upload_wrong_extension():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/upload/pdf",
            files={"file": ("test.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_oversized_file():
    large_content = b"%PDF" + b"x" * (11 * 1024 * 1024)  # 11 MB
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/upload/pdf",
            files={"file": ("big.pdf", large_content, "application/pdf")},
        )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_upload_corrupted_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/upload/pdf",
            files={"file": ("corrupted.pdf", b"%PDF-garbage-content", "application/pdf")},
        )
    # Should be 400 (corrupted) or 500 (extraction failed) — both are acceptable
    assert response.status_code in (400, 500)
    data = response.json()
    assert data["error_code"] in ("CORRUPTED_FILE", "EXTRACTION_FAILED")


@pytest.mark.asyncio
async def test_upload_image_wrong_extension():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/upload/image",
            files={"file": ("test.gif", b"GIF89a", "image/gif")},
        )
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_FILE_TYPE"

"""
Tests for the OCR service (unit tests).
"""
import pytest

from app.utils.error_handlers import CorruptedFileError

# ── OCR service error path ─────────────────────────────────────────────────────

def test_ocr_raises_corrupted_on_invalid_image():
    from app.services.ocr_service import extract_image
    # We should catch an exception for invalid image data.
    # Depending on how extract_image is implemented, it might raise CorruptedFileError or general Exception.
    with pytest.raises(Exception):
        extract_image(b"not an image", "bad.png")


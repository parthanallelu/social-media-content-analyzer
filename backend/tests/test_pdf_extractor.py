"""Tests for the PDF extraction service (unit tests, no HTTP layer)."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.pdf_extractor import _classify_block, _deduplicate_blocks, _split_sentences
from app.models.response_models import BlockType, TextBlock
from app.utils.error_handlers import CorruptedFileError


def test_classify_heading_by_size():
    block_type, level = _classify_block("Introduction", avg_font_size=24.0, is_bold=True, body_font_size=12.0)
    assert block_type == BlockType.HEADING
    assert level == 1  # 24/12 = 2.0x ratio → h1


def test_classify_paragraph():
    block_type, level = _classify_block(
        "This is a normal paragraph of text.", avg_font_size=12.0, is_bold=False, body_font_size=12.0
    )
    assert block_type == BlockType.PARAGRAPH
    assert level is None


def test_classify_bullet_with_dash():
    block_type, level = _classify_block("- First item", avg_font_size=12.0, is_bold=False, body_font_size=12.0)
    assert block_type == BlockType.BULLET


def test_classify_bullet_with_bullet_char():
    block_type, level = _classify_block("• Second item", avg_font_size=12.0, is_bold=False, body_font_size=12.0)
    assert block_type == BlockType.BULLET


def test_classify_numbered_list():
    block_type, level = _classify_block("1. First step", avg_font_size=12.0, is_bold=False, body_font_size=12.0)
    assert block_type == BlockType.BULLET


def test_deduplicate_removes_consecutive_duplicates():
    blocks = [
        TextBlock(type=BlockType.PARAGRAPH, text="Hello", page=1),
        TextBlock(type=BlockType.PARAGRAPH, text="Hello", page=1),
        TextBlock(type=BlockType.PARAGRAPH, text="World", page=1),
    ]
    result = _deduplicate_blocks(blocks)
    assert len(result) == 2
    assert result[0].text == "Hello"
    assert result[1].text == "World"


def test_deduplicate_preserves_non_duplicates():
    blocks = [
        TextBlock(type=BlockType.PARAGRAPH, text="A", page=1),
        TextBlock(type=BlockType.PARAGRAPH, text="B", page=1),
        TextBlock(type=BlockType.PARAGRAPH, text="C", page=1),
    ]
    result = _deduplicate_blocks(blocks)
    assert len(result) == 3


def test_extract_pdf_raises_on_corrupted():
    from app.services.pdf_extractor import extract_pdf
    with pytest.raises(CorruptedFileError):
        extract_pdf(b"not a pdf", "bad.pdf")

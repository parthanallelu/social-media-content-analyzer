import io
import time
import logging
from typing import List

import fitz  # PyMuPDF

from app.models.response_models import TextBlock, BlockType, ExtractionContent, ExtractionMetadata
from app.utils.error_handlers import CorruptedFileError, ExtractionFailedError

logger = logging.getLogger(__name__)

# Font-size ratio thresholds for heading detection relative to body text
HEADING_RATIO_THRESHOLDS = [
    (2.0, 1),   # ≥2x body size → h1
    (1.6, 2),   # ≥1.6x         → h2
    (1.3, 3),   # ≥1.3x         → h3
    (1.1, 4),   # ≥1.1x         → h4
]

BULLET_PREFIXES = ("•", "-", "*", "–", "▪", "◦", "▸", "›")


def extract_pdf(content: bytes, filename: str) -> tuple[ExtractionContent, ExtractionMetadata, int]:
    """
    Extract structured text blocks from a PDF file.

    Args:
        content: Raw PDF file bytes.
        filename: Original filename (for logging).

    Returns:
        Tuple of (ExtractionContent, ExtractionMetadata, page_count).

    Raises:
        CorruptedFileError: If PyMuPDF cannot open the document.
        ExtractionFailedError: On unexpected errors during extraction.
    """
    start_time = time.monotonic()
    doc = _open_pdf(content, filename)

    try:
        page_count = len(doc)
        body_font_size = _estimate_body_font_size(doc)
        blocks: List[TextBlock] = []

        for page_num, page in enumerate(doc, start=1):
            page_blocks = _extract_page_blocks(page, page_num, body_font_size)
            blocks.extend(page_blocks)

        # De-duplicate consecutive identical blocks (artifact of some PDFs)
        blocks = _deduplicate_blocks(blocks)

        char_count = sum(len(b.text) for b in blocks)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        logger.info(
            "PDF extracted: file=%s pages=%d blocks=%d chars=%d time_ms=%d",
            filename, page_count, len(blocks), char_count, elapsed_ms,
        )

        return (
            ExtractionContent(blocks=blocks),
            ExtractionMetadata(processing_time_ms=elapsed_ms, character_count=char_count),
            page_count,
        )
    except (CorruptedFileError, ExtractionFailedError):
        raise
    except Exception as exc:
        logger.exception("Unexpected error during PDF extraction: %s", exc)
        raise ExtractionFailedError(detail=str(exc)) from exc
    finally:
        doc.close()


def _open_pdf(content: bytes, filename: str) -> fitz.Document:
    """Attempt to open a PDF document, raising CorruptedFileError on failure."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        logger.warning("Cannot open PDF '%s': %s", filename, exc)
        raise CorruptedFileError(detail=str(exc)) from exc

    if doc.needs_pass:
        doc.close()
        raise CorruptedFileError(detail="Document is password-protected.")

    if len(doc) == 0:
        doc.close()
        raise CorruptedFileError(detail="PDF contains zero pages.")

    return doc


def _estimate_body_font_size(doc: fitz.Document) -> float:
    """
    Sample pages to find the modal (most common) font size, which we treat as body text.
    Falls back to 12.0 if no spans are found.
    """
    font_size_counts: dict[float, int] = {}
    pages_to_sample = min(len(doc), 5)

    for page in list(doc)[:pages_to_sample]:
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = round(span.get("size", 0), 1)
                    if size > 0:
                        font_size_counts[size] = font_size_counts.get(size, 0) + 1

    if not font_size_counts:
        return 12.0

    return max(font_size_counts, key=font_size_counts.get)  # type: ignore[arg-type]


def _extract_page_blocks(
    page: fitz.Page, page_num: int, body_font_size: float
) -> List[TextBlock]:
    """Extract and classify all text blocks from a single page."""
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    blocks: List[TextBlock] = []

    for raw_block in text_dict.get("blocks", []):
        if raw_block.get("type") != 0:
            continue  # skip image blocks

        block_text, avg_font_size, is_bold = _parse_block_spans(raw_block)

        if not block_text.strip():
            continue

        block_type, level = _classify_block(block_text, avg_font_size, is_bold, body_font_size)
        blocks.append(TextBlock(type=block_type, level=level, text=block_text.strip(), page=page_num))

    return blocks


def _parse_block_spans(raw_block: dict) -> tuple[str, float, bool]:
    """
    Flatten a block's spans into a single text string.
    Also returns the average font size and whether any span is bold.
    """
    texts = []
    font_sizes = []
    is_bold = False

    for line in raw_block.get("lines", []):
        line_texts = []
        for span in line.get("spans", []):
            text = span.get("text", "")
            size = span.get("size", 0.0)
            flags = span.get("flags", 0)

            if text:
                line_texts.append(text)
                if size > 0:
                    font_sizes.append(size)
                # Bit 4 (0b10000 = 16) indicates bold in PyMuPDF flags
                if flags & 16:
                    is_bold = True

        if line_texts:
            texts.append("".join(line_texts))

    block_text = "\n".join(texts)
    avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0.0
    return block_text, avg_size, is_bold


def _classify_block(
    text: str, avg_font_size: float, is_bold: bool, body_font_size: float
) -> tuple[BlockType, int | None]:
    """
    Classify a block as heading, bullet, paragraph, or unknown.
    Returns (BlockType, heading_level | None).
    """
    stripped = text.strip()

    # Bullet detection
    if any(stripped.startswith(p) for p in BULLET_PREFIXES):
        return BlockType.BULLET, None

    # Numbered list: "1.", "2)", "a.", "i."
    import re
    if re.match(r"^(\d+[.)]\s|[a-z][.)]\s|[ivxlc]+[.)]\s)", stripped, re.IGNORECASE):
        return BlockType.BULLET, None

    # Heading detection by font-size ratio
    if body_font_size > 0:
        ratio = avg_font_size / body_font_size
        for threshold, level in HEADING_RATIO_THRESHOLDS:
            if ratio >= threshold:
                return BlockType.HEADING, level

        # Bold text at body size can still be a heading (e.g. section label)
        if is_bold and ratio >= 1.0 and len(stripped) < 120:
            return BlockType.HEADING, 4

    if avg_font_size == 0.0:
        return BlockType.UNKNOWN, None

    return BlockType.PARAGRAPH, None


def _deduplicate_blocks(blocks: List[TextBlock]) -> List[TextBlock]:
    """Remove consecutive duplicate blocks (common in multi-column PDFs)."""
    if not blocks:
        return blocks
    result = [blocks[0]]
    for block in blocks[1:]:
        if block.text != result[-1].text:
            result.append(block)
    return result

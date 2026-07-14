import io
import time
import logging
import math
from typing import List, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.models.response_models import TextBlock, BlockType, ExtractionContent, ExtractionMetadata
from app.utils.error_handlers import CorruptedFileError, OCRFailedError

logger = logging.getLogger(__name__)

# Minimum average confidence (0–100) to consider OCR successful
MIN_CONFIDENCE_THRESHOLD = 10.0
# Target DPI for upscaling; images below this are upscaled
TARGET_DPI = 300


def extract_image(content: bytes, filename: str) -> tuple[ExtractionContent, ExtractionMetadata]:
    """
    Run the full OCR pipeline on an image file:
      1. Load with Pillow
      2. Preprocess with OpenCV (grayscale → deskew → denoise → threshold → upscale)
      3. Run pytesseract with word-level confidence data
      4. Assemble into TextBlock list

    Returns:
        Tuple of (ExtractionContent, ExtractionMetadata).

    Raises:
        CorruptedFileError: If the image cannot be opened.
        OCRFailedError: If Tesseract fails or returns no usable text.
    """
    start_time = time.monotonic()

    # --- Load image ---
    pil_image = _load_image(content, filename)

    # --- Preprocess ---
    preprocessed = _preprocess(pil_image)

    # --- OCR ---
    raw_text, confidence = _run_ocr(preprocessed, filename)

    if not raw_text.strip():
        raise OCRFailedError(
            detail="Tesseract returned no text after preprocessing."
        )

    # --- Parse into blocks ---
    blocks = _text_to_blocks(raw_text)

    char_count = sum(len(b.text) for b in blocks)
    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    logger.info(
        "OCR complete: file=%s blocks=%d chars=%d confidence=%.1f time_ms=%d",
        filename, len(blocks), char_count, confidence, elapsed_ms,
    )

    return (
        ExtractionContent(blocks=blocks),
        ExtractionMetadata(
            processing_time_ms=elapsed_ms,
            character_count=char_count,
            ocr_confidence=round(confidence, 2),
        ),
    )


def _load_image(content: bytes, filename: str) -> Image.Image:
    """Load image bytes with Pillow; raise CorruptedFileError on failure."""
    try:
        pil_image = Image.open(io.BytesIO(content))
        pil_image.verify()  # detect truncated files
        # Re-open after verify (verify exhausts the stream)
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
        return pil_image
    except UnidentifiedImageError as exc:
        raise CorruptedFileError(detail=f"Cannot identify image format: {exc}") from exc
    except Exception as exc:
        logger.warning("Failed to open image '%s': %s", filename, exc)
        raise CorruptedFileError(detail=str(exc)) from exc


def _preprocess(pil_image: Image.Image) -> np.ndarray:
    """
    OpenCV preprocessing pipeline:
      1. Convert RGB → Grayscale
      2. Upscale if below TARGET_DPI equivalent
      3. Deskew
      4. Denoise
      5. Adaptive threshold (binarize)
    Returns a preprocessed numpy array ready for Tesseract.
    """
    img = np.array(pil_image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Upscale small images
    h, w = gray.shape
    if max(h, w) < 1000:
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Deskew
    gray = _deskew(gray)

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # Adaptive threshold (handles uneven lighting)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    return binary


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Detect skew angle and rotate to correct it."""
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 100:
            return gray  # not enough dark pixels to measure skew

        angle = cv2.minAreaRect(coords)[-1]
        # minAreaRect angle is in [-90, 0); convert to actual skew angle
        if angle < -45:
            angle = 90 + angle

        if abs(angle) < 0.5:
            return gray  # negligible skew — skip rotation

        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated
    except Exception as exc:
        logger.debug("Deskew failed (non-fatal): %s", exc)
        return gray


def _run_ocr(preprocessed: np.ndarray, filename: str) -> Tuple[str, float]:
    """
    Run pytesseract on the preprocessed image.
    Returns (full_text, average_confidence).
    """
    try:
        config = "--oem 3 --psm 3"  # OEM 3 = LSTM; PSM 3 = fully automatic
        data = pytesseract.image_to_data(
            preprocessed,
            lang=settings.ocr_language,
            config=config,
            output_type=pytesseract.Output.DICT,
            timeout=settings.ocr_timeout_seconds,
        )
    except RuntimeError as exc:
        logger.error("pytesseract runtime error for '%s': %s", filename, exc)
        raise OCRFailedError(detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected OCR error for '%s': %s", filename, exc)
        raise OCRFailedError(detail=str(exc)) from exc

    # Filter to words with valid confidence
    words = []
    confidences = []
    for i, word in enumerate(data["text"]):
        conf = data["conf"][i]
        if isinstance(conf, (int, float)) and conf >= 0 and word.strip():
            words.append(word)
            confidences.append(float(conf))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    if avg_confidence < MIN_CONFIDENCE_THRESHOLD:
        logger.warning(
            "Low OCR confidence for '%s': %.1f%%", filename, avg_confidence
        )
        raise OCRFailedError(
            detail=f"OCR confidence too low ({avg_confidence:.1f}%). "
                   "Image may be blurry, too dark, or contain no readable text."
        )

    # Reconstruct text using pytesseract's plain text (preserves line structure)
    full_text = pytesseract.image_to_string(
        preprocessed,
        lang=settings.ocr_language,
        config=config,
        timeout=settings.ocr_timeout_seconds,
    )

    return full_text, avg_confidence


def _text_to_blocks(raw_text: str) -> List[TextBlock]:
    """
    Convert raw OCR text string into TextBlock list.
    Paragraphs are separated by double newlines; single newlines are joined.
    """
    blocks: List[TextBlock] = []
    # Split on paragraph breaks (blank lines)
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

    for para in paragraphs:
        # Join wrapped lines within a paragraph
        text = " ".join(line.strip() for line in para.splitlines() if line.strip())
        if text:
            blocks.append(TextBlock(type=BlockType.PARAGRAPH, level=None, text=text, page=1))

    return blocks if blocks else [TextBlock(type=BlockType.UNKNOWN, level=None, text=raw_text.strip(), page=1)]

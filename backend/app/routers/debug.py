"""
Debug router — OCR preprocessing comparison endpoint.

POST /debug/ocr-compare  (multipart: file)

Returns a JSON report comparing different preprocessing variants
against the uploaded image, including confidence scores and extracted
text for each variant. This allows visual inspection of what
Tesseract actually sees after preprocessing.

This endpoint is intentionally NOT included in production routing
unless the DEBUG_OCR environment variable is set to "1".
"""

import io
import base64
import time
import math
import logging

import cv2
import numpy as np
import pytesseract
from PIL import Image
from fastapi import APIRouter, File, UploadFile

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/debug", tags=["Debug"])


def _run_ocr(image_array, label=""):
    """Run Tesseract and return (text, confidence, elapsed_ms)."""
    config = "--oem 3 --psm 3"
    t0 = time.monotonic()

    data = pytesseract.image_to_data(
        image_array, lang=settings.ocr_language, config=config,
        output_type=pytesseract.Output.DICT,
        timeout=settings.ocr_timeout_seconds,
    )
    confidences = []
    for i, word in enumerate(data["text"]):
        conf = data["conf"][i]
        if isinstance(conf, (int, float)) and conf >= 0 and word.strip():
            confidences.append(float(conf))

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    full_text = pytesseract.image_to_string(
        image_array, lang=settings.ocr_language, config=config,
        timeout=settings.ocr_timeout_seconds,
    )
    elapsed = int((time.monotonic() - t0) * 1000)
    return full_text.strip(), round(avg_conf, 2), elapsed


def _img_to_base64_png(img_array):
    """Encode a numpy image array as a base64 PNG string."""
    if len(img_array.shape) == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array
    _, buf = cv2.imencode(".png", img_bgr)
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _deskew_old(gray):
    """Old broken deskew logic (minAreaRect on all dark pixels)."""
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 100:
            return gray, 0.0
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5:
            return gray, angle
        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated, angle
    except Exception:
        return gray, 0.0


def _deskew_new(gray):
    """New Hough-based deskew logic."""
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, rho=1, theta=np.pi / 180, threshold=100,
            minLineLength=gray.shape[1] // 8, maxLineGap=10,
        )
        if lines is None or len(lines) < 5:
            return gray, 0.0
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            if abs(dx) < 1:
                continue
            angle_deg = math.degrees(math.atan2(dy, dx))
            if abs(angle_deg) < 30:
                angles.append(angle_deg)
        if len(angles) < 3:
            return gray, 0.0
        median_angle = float(np.median(angles))
        if abs(median_angle) < 1.0 or abs(median_angle) > 15.0:
            return gray, median_angle
        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated, median_angle
    except Exception:
        return gray, 0.0


@router.post("/ocr-compare", summary="Compare OCR preprocessing variants")
async def ocr_compare(file: UploadFile = File(...)):
    """
    Upload an image and get a side-by-side comparison of different
    preprocessing strategies. Returns JSON with confidence scores,
    extracted text, deskew angles, and base64-encoded preprocessed
    images for each variant.
    """
    content = await file.read()
    pil_img = Image.open(io.BytesIO(content)).convert("RGB")
    img = np.array(pil_img)

    results = []

    # --- Variant A: No preprocessing (raw RGB) ---
    text, conf, elapsed = _run_ocr(img, "raw")
    results.append({
        "variant": "A",
        "description": "No preprocessing (raw RGB)",
        "confidence": conf,
        "time_ms": elapsed,
        "text_preview": text[:500],
        "deskew_angle": None,
        "image_base64": _img_to_base64_png(img),
    })

    # --- Variant B: Grayscale only ---
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    text, conf, elapsed = _run_ocr(gray, "grayscale")
    results.append({
        "variant": "B",
        "description": "Grayscale only",
        "confidence": conf,
        "time_ms": elapsed,
        "text_preview": text[:500],
        "deskew_angle": None,
        "image_base64": _img_to_base64_png(gray),
    })

    # --- Variant C: Grayscale + upscale (new production pipeline minus deskew) ---
    gray_up = gray.copy()
    h, w = gray_up.shape
    if max(h, w) < 1000:
        gray_up = cv2.resize(gray_up, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    text, conf, elapsed = _run_ocr(gray_up, "grayscale+upscale")
    results.append({
        "variant": "C",
        "description": "Grayscale + upscale (NEW production pipeline)",
        "confidence": conf,
        "time_ms": elapsed,
        "text_preview": text[:500],
        "deskew_angle": None,
        "image_base64": _img_to_base64_png(gray_up),
    })

    # --- Variant D: OLD full pipeline (grayscale → upscale → old deskew → denoise → threshold) ---
    gray_old = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    h, w = gray_old.shape
    if max(h, w) < 1000:
        gray_old = cv2.resize(gray_old, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray_old, old_angle = _deskew_old(gray_old)
    gray_old = cv2.fastNlMeansDenoising(gray_old, h=10, templateWindowSize=7, searchWindowSize=21)
    binary = cv2.adaptiveThreshold(
        gray_old, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10,
    )
    text, conf, elapsed = _run_ocr(binary, "old_full_pipeline")
    results.append({
        "variant": "D",
        "description": "OLD full pipeline (grayscale→upscale→deskew→denoise→threshold)",
        "confidence": conf,
        "time_ms": elapsed,
        "text_preview": text[:500],
        "deskew_angle": round(old_angle, 2),
        "image_base64": _img_to_base64_png(binary),
    })

    # Summary
    best = max(results, key=lambda r: r["confidence"])
    worst = min(results, key=lambda r: r["confidence"])

    return {
        "filename": file.filename,
        "image_size": f"{pil_img.size[0]}x{pil_img.size[1]}",
        "variants": results,
        "best_variant": f"{best['variant']} — {best['description']} ({best['confidence']}%)",
        "worst_variant": f"{worst['variant']} — {worst['description']} ({worst['confidence']}%)",
        "recommendation": (
            "The OLD pipeline is NOT best — preprocessing was degrading OCR quality."
            if best["variant"] != "D"
            else "The OLD pipeline performed best — this is unexpected."
        ),
    }

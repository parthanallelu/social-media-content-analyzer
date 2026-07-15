"""
OCR Preprocessing Debug Script
==============================
Tests each preprocessing variant against the same input image and reports:
  - Confidence score
  - Extracted text (first 300 chars)
  - Saves the preprocessed image so you can visually inspect what Tesseract sees

Usage:
  python -m tests.ocr_debug <path_to_image>

Variants tested:
  A) No preprocessing (raw RGB → Tesseract)
  B) Grayscale only
  C) Grayscale + upscale only
  D) Grayscale + deskew only
  E) Grayscale + denoise only
  F) Grayscale + adaptive threshold only
  G) Full current pipeline (grayscale → upscale → deskew → denoise → threshold)
"""

import sys
import os
import io
import time

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_ocr(image_array, label=""):
    """Run Tesseract on an image (numpy array, any channels) and return (text, confidence, elapsed_ms)."""
    config = "--oem 3 --psm 3"
    t0 = time.monotonic()
    data = pytesseract.image_to_data(
        image_array, lang="eng", config=config, output_type=pytesseract.Output.DICT
    )
    confidences = []
    for i, word in enumerate(data["text"]):
        conf = data["conf"][i]
        if isinstance(conf, (int, float)) and conf >= 0 and word.strip():
            confidences.append(float(conf))
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    full_text = pytesseract.image_to_string(image_array, lang="eng", config=config)
    elapsed = int((time.monotonic() - t0) * 1000)
    return full_text.strip(), round(avg_conf, 2), elapsed


def deskew(gray):
    """Current deskew logic from ocr_service.py — verbatim copy."""
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


def save_debug_image(img_array, out_dir, name):
    """Save a numpy array as PNG for visual inspection."""
    path = os.path.join(out_dir, f"{name}.png")
    if len(img_array.shape) == 3:
        cv2.imwrite(path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
    else:
        cv2.imwrite(path, img_array)
    return path


# ---------------------------------------------------------------------------
# Preprocessing variants
# ---------------------------------------------------------------------------

def variant_a_raw(pil_img):
    """No preprocessing at all — raw RGB."""
    return np.array(pil_img)


def variant_b_grayscale(pil_img):
    """Grayscale only."""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)


def variant_c_grayscale_upscale(pil_img):
    """Grayscale + upscale (if small)."""
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if max(h, w) < 1000:
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    return gray


def variant_d_grayscale_deskew(pil_img):
    """Grayscale + deskew only."""
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    deskewed, angle = deskew(gray)
    return deskewed, angle


def variant_e_grayscale_denoise(pil_img):
    """Grayscale + denoise only."""
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def variant_f_grayscale_threshold(pil_img):
    """Grayscale + adaptive threshold only."""
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10
    )


def variant_g_full_pipeline(pil_img):
    """Full current pipeline: grayscale → upscale → deskew → denoise → threshold."""
    img = np.array(pil_img)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if max(h, w) < 1000:
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray, angle = deskew(gray)
    gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10
    )
    return binary, angle


# ---------------------------------------------------------------------------
# Generate synthetic test image (plain text on white background)
# ---------------------------------------------------------------------------

def generate_test_image():
    """Create a clean screenshot-like image: black text on white background."""
    width, height = 800, 400
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    text_lines = [
        "Social Media Content Analyzer",
        "This is a test image for OCR preprocessing.",
        "It contains plain black text on a white background.",
        "Tesseract should read this with very high confidence.",
        "If this text is garbled, preprocessing is the problem.",
    ]

    # Try to use a reasonable font; fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except (OSError, IOError):
            font = ImageFont.load_default()

    y = 40
    for line in text_lines:
        draw.text((40, y), line, fill="black", font=font)
        y += 55

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Determine input image
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
        if not os.path.isfile(img_path):
            print(f"Error: File not found: {img_path}")
            sys.exit(1)
        pil_img = Image.open(img_path).convert("RGB")
        source_label = os.path.basename(img_path)
    else:
        pil_img = generate_test_image()
        source_label = "synthetic_text_on_white.png"

    print(f"\n{'='*72}")
    print(f"  OCR PREPROCESSING DEBUG — Source: {source_label}")
    print(f"  Image size: {pil_img.size[0]}x{pil_img.size[1]}")
    print(f"{'='*72}\n")

    # Output directory for debug images
    out_dir = os.path.join(os.path.dirname(__file__), "ocr_debug_output")
    os.makedirs(out_dir, exist_ok=True)

    # Save the original
    save_debug_image(np.array(pil_img), out_dir, "00_original")
    if source_label == "synthetic_text_on_white.png":
        pil_img.save(os.path.join(out_dir, "00_original.png"))

    variants = [
        ("A", "No preprocessing (raw RGB)",       lambda: variant_a_raw(pil_img)),
        ("B", "Grayscale only",                    lambda: variant_b_grayscale(pil_img)),
        ("C", "Grayscale + upscale",               lambda: variant_c_grayscale_upscale(pil_img)),
        ("D", "Grayscale + deskew",                lambda: variant_d_grayscale_deskew(pil_img)),
        ("E", "Grayscale + denoise",               lambda: variant_e_grayscale_denoise(pil_img)),
        ("F", "Grayscale + adaptive threshold",    lambda: variant_f_grayscale_threshold(pil_img)),
        ("G", "FULL pipeline (current production)",lambda: variant_g_full_pipeline(pil_img)),
    ]

    results = []
    for letter, desc, fn in variants:
        print(f"--- Variant {letter}: {desc} ---")
        result = fn()

        # Some variants return (image, angle), others just image
        angle = None
        if isinstance(result, tuple):
            img_array, angle = result
        else:
            img_array = result

        # Save preprocessed image
        saved_path = save_debug_image(img_array, out_dir, f"{letter}_{desc.replace(' ', '_').replace('(','').replace(')','')}")

        # Run OCR
        text, conf, elapsed = run_ocr(img_array, desc)

        if angle is not None:
            print(f"  Deskew angle applied: {angle:.2f}°")
        print(f"  Confidence:  {conf}%")
        print(f"  Time:        {elapsed}ms")
        print(f"  Image saved: {saved_path}")
        print(f"  Text (first 300 chars):")
        print(f"    {repr(text[:300])}")
        print()

        results.append({
            "variant": letter,
            "desc": desc,
            "confidence": conf,
            "time_ms": elapsed,
            "text_preview": text[:300],
            "angle": angle,
        })

    # Summary table
    print(f"\n{'='*72}")
    print(f"  SUMMARY TABLE")
    print(f"{'='*72}")
    print(f"  {'Var':<4} {'Confidence':>10}  {'Time':>6}  {'Angle':>7}  {'Description'}")
    print(f"  {'---':<4} {'----------':>10}  {'------':>6}  {'-----':>7}  {'-----------'}")
    for r in results:
        angle_str = f"{r['angle']:.1f}°" if r['angle'] is not None else "N/A"
        print(f"  {r['variant']:<4} {r['confidence']:>9.1f}%  {r['time_ms']:>5}ms  {angle_str:>7}  {r['desc']}")

    # Determine best variant
    best = max(results, key=lambda r: r["confidence"])
    worst = min(results, key=lambda r: r["confidence"])
    print(f"\n  ✓ BEST:  Variant {best['variant']} — {best['desc']} ({best['confidence']}%)")
    print(f"  ✗ WORST: Variant {worst['variant']} — {worst['desc']} ({worst['confidence']}%)")

    if best["variant"] != "G":
        print(f"\n  ⚠ WARNING: The full pipeline (G) is NOT the best-performing variant.")
        print(f"    Consider simplifying preprocessing to Variant {best['variant']}.")

    print(f"\n  Debug images saved to: {out_dir}")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()

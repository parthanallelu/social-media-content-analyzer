# Approach

## Architecture

I built this application using a decoupled, session-scoped frontend (React/Vite/Zustand) and a stateless Python backend (FastAPI). My workflow focused on establishing a robust file processing pipeline first—ensuring files were reliably ingested, validated, and parsed—before layering on the NLP analysis engine and UI polish.

The frontend and backend are deployed independently: the React app ships to **Vercel**, while the FastAPI backend runs inside a **Docker container on Render**. There is no shared database; the backend is completely stateless and the frontend manages all user state via Zustand and browser `localStorage`.

## OCR Pipeline

For image text extraction, I use `pytesseract` backed by Tesseract's LSTM engine (OEM 3), with OpenCV and Pillow handling image preprocessing.

### Preprocessing Philosophy

Early iterations used an aggressive preprocessing pipeline: grayscale conversion → upscaling → deskew → denoising (`fastNlMeansDenoising`) → adaptive thresholding. In production, this consistently produced garbled, unreadable OCR output—especially on screenshots and infographics.

**Root cause analysis** revealed three compounding issues:

1. **Broken deskew logic**: The original implementation used `cv2.minAreaRect()` on all dark pixels (`gray < 128`) to compute a skew angle. For screenshots with UI chrome, icons, and scattered text, this computes the bounding rectangle of the *entire dark pixel cloud*—producing a meaningless rotation angle (often 30–45°) that rotates perfectly straight text into unreadable orientations.

2. **Aggressive denoising**: `cv2.fastNlMeansDenoising(h=10)` blurs the crisp text edges that Tesseract's neural network relies on for glyph recognition.

3. **Adaptive thresholding**: `cv2.adaptiveThreshold(blockSize=31, C=10)` destroys anti-aliased text (the smooth gray sub-pixels at character edges) and introduces high-frequency artifacts that confuse the LSTM recognizer.

### Final Pipeline

The production pipeline is deliberately minimal:

- **Grayscale conversion** — reduces Tesseract's search space to luminance only.
- **Upscaling** — images smaller than 1000px on their longest side are 2× upscaled via bicubic interpolation so Tesseract can resolve individual glyphs.
- **Conservative Hough-based deskew** — replaced `minAreaRect` with `cv2.HoughLinesP` to detect actual horizontal line features (text baselines, borders). The median angle of detected near-horizontal lines is computed, and rotation is only applied when ≥ 5 lines are found, ≥ 3 are near-horizontal, and the median angle falls between 1° and 15°. This prevents catastrophic rotations on non-skewed images while still correcting genuinely scanned documents.

**Deliberately omitted**: adaptive thresholding, heavy denoising. Tesseract's LSTM engine performs best on clean grayscale input.

## PDF Parsing

Instead of flattening PDFs into a single unreadable text blob, I used `PyMuPDF` to traverse document blocks and heuristically classify them by font size and spatial layout into headings, paragraphs, and bullet points—preserving the critical semantic structure that the NLP analysis layer depends on.

## NLP Analysis Engine

The analysis engine relies strictly on rule-based NLP—using `spaCy`, `NLTK`, and `TextBlob`—to extract keywords, determine sentiment polarity, calculate readability metrics (Flesch-Kincaid), detect calls to action, and suggest hashtags. No paid LLM APIs are required.

**Tradeoff**: Rule-based analysis is fast, free, and deterministic, but it lacks the contextual nuance of large language models. For instance, sarcasm and domain-specific jargon can skew sentiment scores. This is an acceptable tradeoff for a portfolio project that needs to run with zero API costs.

## Deployment

### Backend: Render Native → Docker Migration

The backend was initially deployed as a **native Python buildpack** on Render. This worked for the core API but failed for OCR: `pytesseract` requires the `tesseract-ocr` system binary, which is not available in Render's native Python environment.

To solve this, I migrated the deployment to a **Docker-based approach**:

- Created a production `Dockerfile` based on `python:3.11-slim`.
- Installed system-level OCR dependencies (`tesseract-ocr`, `tesseract-ocr-eng`, `libtesseract-dev`, `poppler-utils`) via `apt-get`.
- Pre-downloaded NLTK data (`punkt`, `averaged_perceptron_tagger`, `stopwords`, `wordnet`) at build time to avoid runtime downloads.
- Updated `render.yaml` to use `env: docker` with `dockerContext: backend`.

An earlier attempt to use Render's native Python environment also encountered a **dependency conflict**: `spaCy 3.7.4` requires `typer<0.10.0`, but `fastapi[standard]` pulls in `fastapi-cli` which requires `typer>=0.15.0`. Since we start the server with `uvicorn app.main:app` (not `fastapi dev`), the fix was to install plain `fastapi` without the `[standard]` extras.

### Frontend: Vercel

The React frontend deploys to Vercel with `npm run build` producing a static `dist/` output. The backend URL is configured via `VITE_API_BASE_URL` (or `VITE_API_URL` as a fallback) environment variable.

### CORS Strategy

CORS is configured with **explicit origins only**—never a wildcard. The backend accepts:

- Static origins from `ALLOWED_ORIGIN` env var (localhost for dev, production Vercel URL for prod).
- A **regex pattern** (`allow_origin_regex`) matching Vercel's dynamic preview deployment URLs (`social-media-content-analyzer-*-partha-nallelu.vercel.app`). This was necessary because Vercel generates a unique subdomain for every push, and without regex matching, every preview deploy would fail with CORS errors.

Only `GET` and `POST` methods are permitted; credentials are disabled.

## Frontend UX Decisions

### File Upload

The upload component uses `react-dropzone` for drag-and-drop with a manual "Browse Files" fallback. A cross-platform issue was discovered during testing: on Windows, `react-dropzone`'s MIME-type-based `accept` filter caused the native file picker's "Open" button to remain disabled. The fix was to pass explicit file extensions (`.pdf`, `.png`, `.jpg`, `.jpeg`) directly to the underlying HTML input's `accept` attribute, bypassing the MIME-type lookup.

### Error Handling

The Axios response interceptor normalizes all error shapes—whether the backend returns structured JSON (`{ error_code, message, detail }`), plain text (CORS rejections), or network timeouts—into a consistent format that the UI can display without crashing. Human-readable error messages are mapped from backend `error_code` values via a centralized config lookup.

## Session-Scoped Design

A key architectural decision was making the entire system session-scoped with no backend database. All user state—upload history, extracted text, analysis results—is managed via Zustand stores persisted to browser `localStorage`.

**Tradeoff**: This eliminates database provisioning, server maintenance costs, and user authentication overhead. However, it means user history is strictly tied to their local browser session and cannot be synced across devices or recovered if `localStorage` is cleared. For a portfolio/interview deliverable, this tradeoff significantly reduces deployment complexity while still demonstrating the full end-to-end pipeline.

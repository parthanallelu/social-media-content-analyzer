# Approach

I built this using a decoupled frontend (React/Vite/Zustand) and a stateless Python backend (FastAPI), deployed independently to Vercel and Render (Docker).

My workflow prioritized the file processing pipeline first—reliable ingestion and parsing—before layering on NLP analysis and UI polish.

For **PDF parsing**, I used `PyMuPDF` to traverse document blocks, heuristically classifying them by font size and layout into headings, paragraphs, and bullet points rather than flattening into a single text blob.

For **OCR**, I use `pytesseract` with OpenCV preprocessing. Early iterations applied aggressive deskewing, denoising, and adaptive thresholding, which consistently produced garbled output. Root cause: the deskew logic (`minAreaRect` on all dark pixels) was computing meaningless rotation angles on screenshots. I replaced it with a minimal pipeline—grayscale, upscaling, and conservative Hough-line-based deskew—which dramatically improved accuracy.

The **analysis engine** uses rule-based NLP (`spaCy`, `NLTK`, `TextBlob`) for sentiment, readability, keyword extraction, and hashtag suggestions—no paid LLM APIs required.

The backend was migrated from Render's native Python environment to **Docker** to install Tesseract system dependencies. CORS uses explicit origins plus a regex pattern for Vercel's dynamic preview URLs.

**Key tradeoff**: Session-scoped design with no database eliminates server maintenance but ties history to the browser's `localStorage`.

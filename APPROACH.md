# Approach

I built this application using a decoupled, session-scoped frontend (React/Vite/Zustand) and a stateless Python backend (FastAPI). 

My workflow focused on establishing a robust file processing pipeline first, ensuring files were reliably ingested and parsed, before layering on the NLP analysis and UI polish.

For OCR, I leveraged `pytesseract` integrated via OpenCV and Pillow to handle image pre-processing, yielding high confidence text extraction from raw images.

Instead of flattening PDFs into an unreadable text blob, I used `PyMuPDF` to traverse document blocks, heuristically classifying them by font size and layout into headings, paragraphs, and bullet points to preserve critical semantic structure.

The analysis engine relies strictly on rule-based NLP—using `spaCy`, `NLTK`, and `TextBlob`—to extract keywords, determine sentiment polarity, calculate readability metrics, and suggest hashtags without requiring paid LLM APIs.

A key design decision was making the entire architecture session-scoped with no backend database. State is managed entirely via Zustand and browser `localStorage`. 

**Tradeoff**: While this eliminates database provisioning, server maintenance, and user authentication overhead, it means user history is strictly tied to their local browser session and cannot be synced across devices or recovered if local storage is cleared.

# Social Media Content Analyzer

🔗 **[Live Demo](https://social-media-content-analyzer-qxmivvj9l-partha-nallelu.vercel.app/)**

A production-ready web application designed to help users upload documents or images, extract their text, and analyze the content to generate social media engagement insights. 

Built with a stateless Python backend and a highly responsive React frontend, the app prioritizes a clean, modern SaaS aesthetic.

## Project Overview

This tool allows users to drag-and-drop PDFs or images to instantly extract text. PDFs are parsed semantically (preserving headings and bullet points), while images are processed via OCR. Once extracted, a local rule-based NLP engine analyzes the text to provide actionable insights such as sentiment polarity, readability scores, and hashtag recommendations.

## Features

- **Document Parsing**: Extracts text from PDFs while intelligently preserving semantic formatting (paragraphs, headings, bullet points).
- **Image OCR**: Extracts text from uploaded images with automatic pre-processing and an exposed **OCR Confidence Score**.
- **NLP Analysis Engine**: 
  - Sentiment Analysis & Subjectivity scoring
  - Keyword Frequency extraction (visualized as a horizontal bar chart)
  - Readability and structure metrics
  - Call to Action (CTA) detection
  - Hashtag recommendations & Caption improvements
- **SaaS Dashboard Interface**: Clean, professional design with an integrated **Dark Mode** toggle.
- **Copy & Download**: Export the raw extracted text to clipboard or as a `.txt` file.
- **PDF Export**: Capture and export the rich Analysis Results panel to a `.pdf` file.
- **Session History**: An integrated sidebar tracks your recent uploads and their summary stats across the browser session.

## Architecture

The system utilizes a decoupled, session-scoped architecture:
- **Frontend**: React (Vite), Zustand for state management, TailwindCSS for styling. State is persisted solely in the browser's `localStorage`.
- **Backend**: Python (FastAPI), PyMuPDF (PDFs), Tesseract/OpenCV (Images), and spaCy/NLTK/TextBlob (NLP). 

*There is no database.* The backend is completely stateless, meaning user data is never stored on the server. For a deeper dive into technical decisions, see `APPROACH.md`.

## Folder Structure

```text
social_media_content_analyzer/
├── backend/
│   ├── app/                # FastAPI application logic (routes, services)
│   ├── tests/              # Pytest suites
│   ├── render.yaml         # Render blueprint configuration
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Production Dockerfile
│   ├── runtime.txt         # Pinned local Python runtime
│   └── .env.example        # Environment variable template
├── frontend/
│   ├── src/                # React components, stores, and hooks
│   ├── dist/               # Production build output
│   ├── index.html          # Entry HTML
│   ├── package.json        # Node dependencies
│   ├── tailwind.config.js  # Tailwind theme tokens
│   └── vite.config.js      # Vite bundler config
├── APPROACH.md             # Technical design decisions
└── README.md               # You are here
```

## Known Limitations

- **Render Free-Tier Cold Start**: The backend may take ~30 seconds to wake up on the very first upload. The frontend initiates a pre-warm ping on load to mitigate this.
- **English-Only**: The OCR and NLP models are currently optimized for English text only.
- **Rule-Based Analysis**: The analysis relies on heuristic rules and local models rather than large language models (LLMs).
- **Session-Scoped History**: Because there is no persistent database, the upload history will be permanently lost if the browser's `localStorage` is cleared.

## Future Improvements

- Integrate an optional cloud-based LLM (e.g., OpenAI/Gemini) for highly contextual caption rewriting.
- Support multi-language OCR and NLP processing.
- Add user authentication and a persistent database to save analysis history across devices.

---

## Installation & Running Locally

### Backend Setup

1. **Install Tesseract OCR**: You must have Tesseract installed on your system path.
   - Mac: `brew install tesseract`
   - Windows: Download the installer from UB-Mannheim and add it to your PATH.
2. **Setup Python Environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Run the API**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Install Node Dependencies**:
   ```bash
   cd frontend
   npm install
   ```
2. **Run the Dev Server**:
   ```bash
   npm run dev
   ```

---

## Deployment

### Backend (Render - Docker)

The backend is configured to deploy as a Docker container on Render. This ensures all system-level dependencies for Tesseract OCR (`tesseract-ocr`, `libtesseract-dev`, `poppler-utils`) are pre-configured.

1. Connect your repository to Render.
2. Render will automatically detect the `render.yaml` configuration and deploy it using the **Docker** environment.
3. If setting up manually in the Render dashboard:
   - **Environment**: Select `Docker`
   - **Docker Context**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile`
4. **Environment Variables**:
   - `ALLOWED_ORIGIN`: Set this to your frontend URL (e.g., `https://your-frontend.vercel.app`).
   - `APP_ENV`: Set to `production`.

### Frontend (Vercel)

The frontend is optimized for deployment on Vercel.

1. Connect your repository to Vercel and import the `frontend` directory.
2. **Build Command**: `npm run build`
3. **Output Directory**: `dist`
4. **Environment Variables**:
   - `VITE_API_BASE_URL`: Set this to your deployed Render backend URL (e.g., `https://your-backend.onrender.com`).

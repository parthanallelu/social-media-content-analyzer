FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK data (punkt, punkt_tab, averaged_perceptron_tagger, stopwords, wordnet)
RUN python -m nltk.downloader -d /usr/share/nltk_data \
    punkt punkt_tab averaged_perceptron_tagger stopwords wordnet

# Copy the rest of the application
COPY . .

# Expose port and define entrypoint
EXPOSE 10000
# Enable debug OCR comparison endpoint (set to 0 or remove after testing)
ENV DEBUG_OCR=0
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]

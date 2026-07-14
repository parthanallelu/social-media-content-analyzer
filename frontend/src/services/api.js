import axios from 'axios';
import { API_BASE_URL, AXIOS_TIMEOUT_MS, ERROR_MESSAGES } from '../constants/config';

// ── Axios instance ─────────────────────────────────────────────────────────────
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: AXIOS_TIMEOUT_MS, // 90 seconds — covers Render cold start + slow OCR
  headers: {
    Accept: 'application/json',
  },
});

// ── Response interceptor: normalize errors ────────────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Build a normalized AppError to propagate to calling hooks
    const appError = _normalizeError(error);
    return Promise.reject(appError);
  }
);

/**
 * Normalizes any Axios error into a consistent AppError shape:
 * { code: string, message: string }
 */
function _normalizeError(error) {
  if (error.code === 'ECONNABORTED') {
    return {
      code: 'TIMEOUT',
      message: ERROR_MESSAGES.TIMEOUT,
    };
  }

  if (!error.response) {
    // Network failure (Render down, DNS failure, etc.)
    return {
      code: 'NETWORK_ERROR',
      message: ERROR_MESSAGES.NETWORK_ERROR,
    };
  }

  const { data, status } = error.response;

  // Structured backend error (our AppException format)
  if (data?.error_code) {
    return {
      code: data.error_code,
      message: ERROR_MESSAGES[data.error_code] || data.message || ERROR_MESSAGES.INTERNAL_ERROR,
    };
  }

  // Handle plain text/HTML error responses (e.g. CORS disallowed origin)
  if (typeof data === 'string' && data.trim()) {
    return {
      code: 'API_ERROR',
      message: data,
    };
  }

  // FastAPI 422 validation error
  if (status === 422) {
    return {
      code: 'MISSING_FILE',
      message: ERROR_MESSAGES.MISSING_FILE,
    };
  }

  return {
    code: 'INTERNAL_ERROR',
    message: ERROR_MESSAGES.INTERNAL_ERROR,
  };
}

// ── API functions ──────────────────────────────────────────────────────────────

/**
 * Ping the /health endpoint to pre-warm the Render backend.
 * Resolves silently on success; rejects with AppError on failure.
 */
export async function pingHealth() {
  const response = await apiClient.get('/health');
  return response.data;
}

/**
 * Upload a PDF file and extract structured text.
 * @param {File} file - The PDF File object
 * @param {function(number): void} onUploadProgress - Progress callback (0–100)
 * @returns {Promise<ExtractionResponse>}
 */
export async function uploadPdf(file, onUploadProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/upload/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress?.(percent);
      }
    },
  });

  return response.data;
}

/**
 * Upload an image file and extract text via OCR.
 * @param {File} file - The image File object
 * @param {function(number): void} onUploadProgress - Progress callback (0–100)
 * @returns {Promise<ExtractionResponse>}
 */
export async function uploadImage(file, onUploadProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress?.(percent);
      }
    },
  });

  return response.data;
}

/**
 * Run rule-based engagement analysis on extracted text blocks.
 * @param {TextBlock[]} blocks - Extracted text blocks
 * @param {string} platform - 'instagram' | 'linkedin' | 'twitter' | 'general'
 * @returns {Promise<AnalysisResponse>}
 */
export async function analyzeContent(blocks, platform = 'general') {
  const response = await apiClient.post('/analyze/', {
    blocks,
    context: { platform },
  });
  return response.data;
}

export default apiClient;

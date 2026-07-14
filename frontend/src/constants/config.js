// App-wide constants — sourced from environment variables where applicable

/** Maximum allowed file size: 10 MB */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;

/** Accepted file extensions */
export const ACCEPTED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg'];

/** react-dropzone accept map */
export const DROPZONE_ACCEPT = {
  'application/pdf': ['.pdf'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
};

/** Backend base URL — uses proxy in dev, full URL in production */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/** Axios timeout in milliseconds: 90s to cover Render cold start + OCR */
export const AXIOS_TIMEOUT_MS = 90_000;

/** Max concurrent upload slots */
export const MAX_CONCURRENT_UPLOADS = 3;

/** File status enum values */
export const FILE_STATUS = {
  IDLE: 'idle',
  UPLOADING: 'uploading',
  EXTRACTING: 'extracting',
  DONE: 'done',
  ERROR: 'error',
  ANALYZING: 'analyzing',
};

/** Severity display config */
export const SEVERITY_CONFIG = {
  high: { label: 'High', color: 'text-danger-400', bg: 'bg-danger-500/10 border-danger-500/20' },
  medium: { label: 'Medium', color: 'text-warning-400', bg: 'bg-warning-500/10 border-warning-500/20' },
  low: { label: 'Low', color: 'text-success-400', bg: 'bg-success-500/10 border-success-500/20' },
};

/** Platform options for analysis */
export const PLATFORMS = [
  { value: 'general', label: 'General' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'twitter', label: 'Twitter / X' },
];

/** Human-readable error messages keyed by backend error_code */
export const ERROR_MESSAGES = {
  INVALID_FILE_TYPE: 'Only PDF, PNG, JPG, and JPEG files are supported.',
  FILE_TOO_LARGE: 'File exceeds the 10 MB limit. Please compress or trim it.',
  CORRUPTED_FILE: 'This file appears corrupted or password-protected and couldn\'t be read.',
  MISSING_FILE: 'No file was received by the server. Please try again.',
  EXTRACTION_FAILED: 'Text extraction failed unexpectedly. Please try a different file.',
  OCR_FAILED: 'Text couldn\'t be extracted from this image. Try a higher-quality scan.',
  ANALYSIS_FAILED: 'Engagement analysis failed. Your extracted text is still available.',
  EMPTY_CONTENT: 'No text content was provided for analysis.',
  NETWORK_ERROR: 'Couldn\'t reach the server. Check your connection and try again.',
  TIMEOUT: 'Processing took too long. Please try again — large or complex files may need more time.',
  INTERNAL_ERROR: 'An unexpected server error occurred. Please try again.',
};

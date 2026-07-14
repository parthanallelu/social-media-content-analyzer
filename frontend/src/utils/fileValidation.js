import { MAX_FILE_SIZE, ACCEPTED_EXTENSIONS, ERROR_MESSAGES } from '../constants/config';

/**
 * Client-side file validation — first line of defense before any API call.
 *
 * @param {File} file
 * @returns {{ valid: boolean, error: { code: string, message: string } | null }}
 */
export function validateFile(file) {
  if (!file) {
    return { valid: false, error: { code: 'MISSING_FILE', message: ERROR_MESSAGES.MISSING_FILE } };
  }

  // Size check
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: { code: 'FILE_TOO_LARGE', message: ERROR_MESSAGES.FILE_TOO_LARGE },
    };
  }

  // Extension check
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: { code: 'INVALID_FILE_TYPE', message: ERROR_MESSAGES.INVALID_FILE_TYPE },
    };
  }

  return { valid: true, error: null };
}

/**
 * Determine file category from its MIME type or extension.
 * @param {File} file
 * @returns {'pdf' | 'image'}
 */
export function getFileType(file) {
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
    return 'pdf';
  }
  return 'image';
}

/**
 * Format bytes into a human-readable string (e.g., "2.4 MB").
 * @param {number} bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Format milliseconds into a human-readable duration string.
 * @param {number} ms
 * @returns {string}
 */
export function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

/**
 * Clamp a number between min and max.
 * @param {number} value
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

/**
 * Compute SVG stroke-dashoffset for a circular score ring.
 * Circumference = 2π × r = 2π × 35 ≈ 220
 * @param {number} score - 0 to 100
 * @returns {number}
 */
export function scoreToOffset(score) {
  const circumference = 220;
  return circumference - (score / 100) * circumference;
}

/**
 * Get a color class based on score value.
 * @param {number} score
 * @returns {string} Tailwind text color class
 */
export function scoreToColorClass(score) {
  if (score >= 75) return 'text-success-400';
  if (score >= 50) return 'text-warning-400';
  return 'text-danger-400';
}

/**
 * Get a stroke color based on score value (for SVG).
 * @param {number} score
 * @returns {string}
 */
export function scoreToStrokeColor(score) {
  if (score >= 75) return '#34d399'; // success-400
  if (score >= 50) return '#fbbf24'; // warning-400
  return '#f87171';                  // danger-400
}

/**
 * Truncate a filename if it's too long.
 * @param {string} name
 * @param {number} maxLength
 * @returns {string}
 */
export function truncateFilename(name, maxLength = 32) {
  if (name.length <= maxLength) return name;
  const ext = name.includes('.') ? '.' + name.split('.').pop() : '';
  const base = name.slice(0, maxLength - ext.length - 3);
  return `${base}...${ext}`;
}

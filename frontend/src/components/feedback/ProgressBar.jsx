import clsx from 'clsx';

/**
 * Progress bar — supports both determinate (0–100%) and indeterminate (infinite shimmer) modes.
 *
 * @param {number|null} value - 0–100 for determinate; null for indeterminate
 * @param {string} label - Accessible label text shown below the bar
 * @param {'primary'|'success'|'warning'|'danger'} color
 */
export default function ProgressBar({ value = null, label, color = 'primary', className = '' }) {
  const isDeterminate = value !== null;

  const trackColor = {
    primary: 'bg-primary-600/20',
    success: 'bg-success-500/20',
    warning: 'bg-warning-500/20',
    danger: 'bg-danger-500/20',
  }[color];

  const fillGradient = {
    primary: 'from-primary-600 to-accent-500',
    success: 'from-success-500 to-emerald-400',
    warning: 'from-warning-500 to-amber-400',
    danger: 'from-danger-500 to-rose-400',
  }[color];

  return (
    <div className={clsx('w-full', className)}>
      <div
        className={clsx('w-full h-1.5 rounded-full overflow-hidden', trackColor)}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={isDeterminate ? value : undefined}
        aria-label={label}
      >
        {isDeterminate ? (
          <div
            className={clsx('h-full rounded-full bg-gradient-to-r transition-all duration-300 ease-out', fillGradient)}
            style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
          />
        ) : (
          // Indeterminate: animated sliding bar
          <div className={clsx('h-full w-1/3 rounded-full bg-gradient-to-r progress-indeterminate', fillGradient)} />
        )}
      </div>
      {label && (
        <p className="mt-1.5 text-xs text-content-faint font-medium">{label}</p>
      )}
    </div>
  );
}

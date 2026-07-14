import { ExclamationTriangleIcon, XCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

const VARIANT_CONFIG = {
  error: {
    Icon: XCircleIcon,
    bg: 'bg-danger-500/10 border-danger-500/25',
    icon: 'text-danger-400',
    text: 'text-danger-300',
  },
  warning: {
    Icon: ExclamationTriangleIcon,
    bg: 'bg-warning-500/10 border-warning-500/25',
    icon: 'text-warning-400',
    text: 'text-warning-300',
  },
  info: {
    Icon: InformationCircleIcon,
    bg: 'bg-accent-500/10 border-accent-500/25',
    icon: 'text-accent-400',
    text: 'text-accent-300',
  },
};

/**
 * Contextual error/warning/info banner.
 * @param {string} message - User-facing message
 * @param {'error'|'warning'|'info'} variant
 * @param {string} className
 */
export default function ErrorBanner({ message, variant = 'error', className = '' }) {
  if (!message) return null;

  const config = VARIANT_CONFIG[variant] ?? VARIANT_CONFIG.error;
  const { Icon } = config;

  return (
    <div
      role="alert"
      className={clsx(
        'flex items-start gap-3 px-4 py-3 rounded-xl border text-sm animate-slide-down',
        config.bg,
        className,
      )}
    >
      <Icon className={clsx('w-5 h-5 flex-shrink-0 mt-0.5', config.icon)} aria-hidden="true" />
      <p className={clsx('leading-relaxed', config.text)}>{message}</p>
    </div>
  );
}

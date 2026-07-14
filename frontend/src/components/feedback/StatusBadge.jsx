import clsx from 'clsx';
import { FILE_STATUS } from '../../constants/config';

const STATUS_CONFIG = {
  [FILE_STATUS.IDLE]: {
    label: 'Queued',
    dot: 'bg-slate-500',
    text: 'text-content-muted',
    bg: 'bg-slate-500/10 border-slate-500/20',
  },
  [FILE_STATUS.UPLOADING]: {
    label: 'Uploading',
    dot: 'bg-accent-400 animate-pulse',
    text: 'text-accent-400',
    bg: 'bg-accent-500/10 border-accent-500/20',
  },
  [FILE_STATUS.EXTRACTING]: {
    label: 'Extracting',
    dot: 'bg-primary-400 animate-pulse',
    text: 'text-primary-400',
    bg: 'bg-primary-500/10 border-primary-500/20',
  },
  [FILE_STATUS.ANALYZING]: {
    label: 'Analyzing',
    dot: 'bg-warning-400 animate-pulse',
    text: 'text-warning-400',
    bg: 'bg-warning-500/10 border-warning-500/20',
  },
  [FILE_STATUS.DONE]: {
    label: 'Done',
    dot: 'bg-success-400',
    text: 'text-success-400',
    bg: 'bg-success-500/10 border-success-500/20',
  },
  [FILE_STATUS.ERROR]: {
    label: 'Failed',
    dot: 'bg-danger-400',
    text: 'text-danger-400',
    bg: 'bg-danger-500/10 border-danger-500/20',
  },
};

/**
 * Small pill-shaped status badge showing the current file processing state.
 * @param {string} status - One of FILE_STATUS values
 */
export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG[FILE_STATUS.IDLE];

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border',
        config.text,
        config.bg,
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', config.dot)} />
      {config.label}
    </span>
  );
}

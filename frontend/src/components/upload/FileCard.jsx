import { DocumentTextIcon, PhotoIcon, XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';
import useFileStore from '../../store/fileStore';
import StatusBadge from '../feedback/StatusBadge';
import ProgressBar from '../feedback/ProgressBar';
import ErrorBanner from '../feedback/ErrorBanner';
import { FILE_STATUS } from '../../constants/config';
import { truncateFilename } from '../../utils/formatters';
import { formatFileSize } from '../../utils/fileValidation';

/**
 * FileCard — represents a single file in the upload queue.
 * Shows status, progress, and error in a compact card.
 *
 * @param {string} fileId
 */
export default function FileCard({ fileId }) {
  const file = useFileStore((s) => s.files.find((f) => f.id === fileId));
  const removeFile = useFileStore((s) => s.removeFile);
  const setActiveFileId = useFileStore((s) => s.setActiveFileId);
  const activeFileId = useFileStore((s) => s.activeFileId);

  if (!file) return null;

  const isActive = activeFileId === fileId;
  const isClickable = file.status === FILE_STATUS.DONE;

  const handleClick = () => {
    if (isClickable) setActiveFileId(fileId);
  };

  const FileIcon = file.fileType === 'pdf' ? DocumentTextIcon : PhotoIcon;

  // Progress bar config per status
  const progressConfig = {
    [FILE_STATUS.UPLOADING]: {
      value: file.progress,
      label: `Uploading… ${file.progress}%`,
      color: 'primary',
    },
    [FILE_STATUS.EXTRACTING]: {
      value: null, // indeterminate
      label: file.fileType === 'image'
        ? 'Running OCR — this may take 10–30s…'
        : 'Extracting text…',
      color: 'primary',
    },
    [FILE_STATUS.ANALYZING]: {
      value: null,
      label: 'Analyzing engagement…',
      color: 'warning',
    },
  }[file.status];

  return (
    <div
      onClick={handleClick}
      className={clsx(
        'relative group flex flex-col gap-3 p-4 rounded-xl border transition-all duration-200',
        isClickable && 'cursor-pointer',
        isActive
          ? 'border-primary-600/50 bg-primary-600/10 shadow-glow-primary'
          : 'border-subtle bg-surface-700 hover:border-strong',
        file.status === FILE_STATUS.ERROR && 'border-danger-500/30 bg-danger-500/5',
      )}
      aria-label={`File: ${file.name} — Status: ${file.status}`}
    >
      {/* Header row */}
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={clsx(
          'flex-shrink-0 p-2 rounded-lg border',
          file.status === FILE_STATUS.ERROR
            ? 'bg-danger-500/10 border-danger-500/25 text-danger-400'
            : 'bg-surface-600 border-subtle text-content-muted',
        )}>
          <FileIcon className="w-5 h-5" />
        </div>

        {/* Name and size */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-content-main truncate" title={file.name}>
            {truncateFilename(file.name)}
          </p>
          <p className="text-xs text-content-faint mt-0.5">{formatFileSize(file.size)}</p>
        </div>

        {/* Status badge + remove button */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge status={file.status} />
          {(file.status === FILE_STATUS.DONE || file.status === FILE_STATUS.ERROR) && (
            <button
              onClick={(e) => { e.stopPropagation(); removeFile(fileId); }}
              className="btn-ghost p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label={`Remove ${file.name}`}
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {progressConfig && (
        <ProgressBar
          value={progressConfig.value}
          label={progressConfig.label}
          color={progressConfig.color}
        />
      )}

      {/* Error message */}
      {file.status === FILE_STATUS.ERROR && file.error && (
        <ErrorBanner message={file.error.message} variant="error" />
      )}

      {/* Done — click to view hint */}
      {file.status === FILE_STATUS.DONE && !isActive && (
        <p className="text-xs text-content-faint opacity-0 group-hover:opacity-100 transition-opacity">
          Click to view extracted text →
        </p>
      )}
    </div>
  );
}

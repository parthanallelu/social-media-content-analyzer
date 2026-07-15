import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentIcon, PhotoIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { DROPZONE_ACCEPT, MAX_FILE_SIZE } from '../../constants/config';
import { useFileUpload } from '../../hooks/useFileUpload';

/**
 * DropZone — react-dropzone wrapper with drag-and-drop + fallback file picker.
 * Handles multiple files per session (up to browser limits).
 */
export default function DropZone() {
  const { enqueueFiles } = useFileUpload();

  const onDrop = useCallback((acceptedFiles, fileRejections) => {
    const allFiles = [
      ...acceptedFiles,
      ...fileRejections.map((r) => r.file),
    ];
    if (allFiles.length > 0) {
      enqueueFiles(allFiles);
    }
  }, [enqueueFiles]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: DROPZONE_ACCEPT,
    maxSize: MAX_FILE_SIZE,
    multiple: true,
    // Note: maxSize is informational here — we do our own validation in enqueueFiles
    // so all files pass through for consistent error display in FileCard
    validator: () => null,
  });

  return (
    <div
      {...getRootProps()}
      id="dropzone"
      className={clsx(
        'relative group cursor-pointer rounded-xl border-2 border-dashed',
        'transition-all duration-300 ease-out',
        'flex flex-col items-center justify-center gap-5 p-12 text-center',
        'min-h-[280px]',
        isDragActive && !isDragReject && [
          'border-primary-500 bg-primary-600/10 dropzone-active',
          'shadow-glow-primary',
        ],
        isDragReject && 'border-danger-500 bg-danger-500/10',
        !isDragActive && [
          'border-subtle bg-surface-800',
          'hover:border-primary-600/50 hover:bg-surface-700',
        ],
      )}
      aria-label="File drop zone — drag and drop PDF or image files here, or click to browse"
    >
      {/* Hidden file input (fallback picker) */}
      <input {...getInputProps({ accept: '.pdf,.png,.jpg,.jpeg' })} id="file-input" aria-label="File input" />

      {/* Decorative background gradient */}
      <div className="absolute inset-0 rounded-xl bg-gradient-radial from-primary-600/5 via-transparent to-transparent pointer-events-none" />

      {/* Icon cluster */}
      <div className="relative flex items-end justify-center gap-2">
        <div className={clsx(
          'p-3 rounded-xl border transition-all duration-300',
          isDragActive
            ? 'bg-primary-600/30 border-primary-500/50 scale-110'
            : 'bg-surface-600 border-subtle group-hover:bg-primary-600/20 group-hover:border-primary-600/40',
        )}>
          <CloudArrowUpIcon className={clsx(
            'w-10 h-10 transition-colors duration-300',
            isDragActive ? 'text-primary-400' : 'text-content-muted group-hover:text-primary-400',
          )} />
        </div>
        <div className="p-2 rounded-xl bg-surface-600 border border-subtle -mb-1 opacity-60">
          <DocumentIcon className="w-6 h-6 text-content-faint" />
        </div>
        <div className="p-2 rounded-xl bg-surface-600 border border-subtle -mb-1 opacity-60">
          <PhotoIcon className="w-6 h-6 text-content-faint" />
        </div>
      </div>

      {/* Text */}
      <div className="relative space-y-2">
        {isDragReject ? (
          <p className="text-lg font-semibold text-danger-400">Unsupported file type</p>
        ) : isDragActive ? (
          <p className="text-lg font-semibold text-primary-400 animate-bounce-subtle">Drop to upload</p>
        ) : (
          <>
            <p className="text-lg font-semibold text-content-main">
              Drag &amp; drop files here
            </p>
            <p className="text-sm text-content-faint">
              or{' '}
              <span className="text-primary-400 font-medium underline underline-offset-2">
                browse your computer
              </span>
            </p>
          </>
        )}
        <p className="text-xs text-content-faint">
          PDF · PNG · JPG · JPEG &nbsp;&bull;&nbsp; Max 10 MB each &nbsp;&bull;&nbsp; Multiple files supported
        </p>
      </div>
    </div>
  );
}

import useFileStore from '../../store/fileStore';
import FileCard from './FileCard';
import Button from '../common/Button';
import { TrashIcon } from '@heroicons/react/24/outline';

/**
 * FileQueue — renders the list of all files in the current session,
 * with a "Clear all" option.
 */
export default function FileQueue() {
  const files = useFileStore((s) => s.files);
  const clearAll = useFileStore((s) => s.clearAll);

  if (files.length === 0) return null;

  return (
    <section aria-label="Upload queue" className="animate-slide-up">
      {/* Section header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-content-muted uppercase tracking-wider">
          Files ({files.length})
        </h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={clearAll}
          className="text-content-faint hover:text-danger-400"
          aria-label="Clear all files"
        >
          <TrashIcon className="w-4 h-4" />
          Clear all
        </Button>
      </div>

      {/* File cards */}
      <div className="flex flex-col gap-2">
        {files.map((file) => (
          <FileCard key={file.id} fileId={file.id} />
        ))}
      </div>
    </section>
  );
}

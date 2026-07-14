import { useState } from 'react';
import { DocumentTextIcon, SparklesIcon, DocumentMagnifyingGlassIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';
import useFileStore from '../../store/fileStore';
import ExtractedText from './ExtractedText';
import AnalysisSuggestions from './AnalysisSuggestions';
import { FILE_STATUS } from '../../constants/config';
import { truncateFilename } from '../../utils/formatters';

const TABS = [
  { id: 'extracted', label: 'Extracted Text', Icon: DocumentTextIcon },
  { id: 'analysis', label: 'Engagement Analysis', Icon: SparklesIcon },
];

/**
 * ResultPanel — tabbed results view for the active (selected) file.
 * Only shown when at least one file is DONE.
 */
export default function ResultPanel() {
  const [activeTab, setActiveTab] = useState('extracted');
  const doneFiles = useFileStore((s) => s.files.filter((f) => f.status === FILE_STATUS.DONE));
  const activeFileId = useFileStore((s) => s.activeFileId);
  const setActiveFileId = useFileStore((s) => s.setActiveFileId);
  const activeFile = useFileStore((s) => s.files.find((f) => f.id === activeFileId));

  if (doneFiles.length === 0) return null;

  // Ensure activeFileId points to a done file
  const displayFile = (activeFile?.status === FILE_STATUS.DONE ? activeFile : doneFiles[0]);

  return (
    <section
      aria-label="Extraction results"
      className="card border-gradient animate-slide-up"
    >
      {/* File selector tabs (when multiple done) */}
      {doneFiles.length > 1 && (
        <div className="flex items-center gap-1 px-4 pt-4 pb-0 overflow-x-auto">
          {doneFiles.map((f) => (
            <button
              key={f.id}
              onClick={() => setActiveFileId(f.id)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-xs font-medium',
                'border-b-2 transition-all duration-150 whitespace-nowrap',
                f.id === displayFile.id
                  ? 'text-primary-400 border-primary-500 bg-primary-600/10'
                  : 'text-content-faint border-transparent hover:text-content-main hover:border-strong',
              )}
              aria-label={`View results for ${f.name}`}
            >
              <DocumentMagnifyingGlassIcon className="w-3.5 h-3.5" />
              {truncateFilename(f.name, 24)}
            </button>
          ))}
        </div>
      )}

      {/* Content tab switcher */}
      <div className="px-6 pt-5">
        <div className="flex items-center gap-1 border-b border-subtle mb-5">
          {TABS.map((tab) => {
            const { Icon } = tab;
            return (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                role="tab"
                aria-selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'flex items-center gap-2 px-4 py-3 text-sm font-medium',
                  'border-b-2 -mb-px transition-all duration-150',
                  activeTab === tab.id
                    ? 'text-primary-400 border-primary-500'
                    : 'text-content-faint border-transparent hover:text-content-main',
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab panels */}
        <div
          role="tabpanel"
          aria-labelledby={`tab-${activeTab}`}
          className="pb-6"
        >
          {activeTab === 'extracted' && displayFile && (
            <ExtractedText result={displayFile.result} />
          )}
          {activeTab === 'analysis' && displayFile && (
            <AnalysisSuggestions fileId={displayFile.id} />
          )}
        </div>
      </div>
    </section>
  );
}

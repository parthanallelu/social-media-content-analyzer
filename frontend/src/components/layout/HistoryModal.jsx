import React from 'react';
import { XMarkIcon, DocumentTextIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import useHistoryStore from '../../store/useHistoryStore';

export default function HistoryModal() {
  const { history, isModalOpen, setModalOpen, clearHistory } = useHistoryStore();

  if (!isModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-content-main/20 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-surface-800 h-full shadow-card flex flex-col transform transition-transform animate-slide-up sm:animate-none">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-subtle">
          <h2 className="text-lg font-bold text-content-main">Upload History</h2>
          <button
            onClick={() => setModalOpen(false)}
            className="p-1 rounded-lg text-content-muted hover:bg-surface-700 hover:text-content-main transition-colors"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {history.length === 0 ? (
            <div className="text-center text-content-faint mt-10">
              <DocumentTextIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No uploads yet.</p>
              <p className="text-xs mt-1">Files you process will appear here during this session.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {history.map((entry, idx) => (
                <div key={entry.id || idx} className="bg-surface-700 border border-subtle p-4 rounded-xl">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm font-bold text-content-main truncate pr-4" title={entry.filename}>
                      {entry.filename}
                    </p>
                    <span className="text-xs text-content-muted whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  
                  {entry.summary && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {entry.summary.wordCount && (
                        <div className="flex items-center gap-1 text-xs text-content-faint bg-surface-800 px-2 py-1 rounded-md border border-subtle">
                          <DocumentTextIcon className="w-3.5 h-3.5" />
                          {entry.summary.wordCount} words
                        </div>
                      )}
                      {entry.summary.sentiment && (
                        <div className="flex items-center gap-1 text-xs text-content-faint bg-surface-800 px-2 py-1 rounded-md border border-subtle capitalize">
                          <ChartBarIcon className="w-3.5 h-3.5" />
                          {entry.summary.sentiment}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {history.length > 0 && (
          <div className="p-4 border-t border-subtle bg-surface-800">
            <button
              onClick={clearHistory}
              className="w-full btn-secondary text-danger-500 hover:text-danger-600 justify-center"
            >
              Clear History
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

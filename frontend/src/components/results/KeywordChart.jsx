import React from 'react';

/**
 * Renders a horizontal bar chart representing word frequency.
 * @param {{keywords: Array<{word: string, frequency: number, score: number}>}} props
 */
export default function KeywordChart({ keywords }) {
  if (!keywords || keywords.length === 0) return null;

  // Find max frequency for scale
  const maxFreq = Math.max(...keywords.map((kw) => kw.frequency));

  return (
    <div className="space-y-3">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold text-content-muted uppercase tracking-wider mb-2">
        Word Frequency Chart
      </h3>
      <div className="space-y-2">
        {keywords.map((kw) => {
          const percentage = Math.max(5, (kw.frequency / maxFreq) * 100);
          return (
            <div key={kw.word} className="flex items-center gap-3">
              {/* Word label */}
              <div className="w-24 shrink-0 text-sm font-medium text-content-main truncate text-right">
                {kw.word}
              </div>
              
              {/* Bar */}
              <div className="flex-1 h-5 bg-surface-700 rounded-sm overflow-hidden flex items-center">
                <div
                  className="h-full bg-primary-500 rounded-sm"
                  style={{ width: `${percentage}%` }}
                />
              </div>

              {/* Count */}
              <div className="w-8 shrink-0 text-xs text-content-faint font-semibold">
                {kw.frequency}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

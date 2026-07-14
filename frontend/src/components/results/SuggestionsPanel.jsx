import { useState } from 'react';
import { LightBulbIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';
import { SEVERITY_CONFIG } from '../../constants/config';

const CATEGORY_COLORS = {
  readability: 'text-blue-400',
  engagement:  'text-purple-400',
  structure:   'text-amber-400',
  platform:    'text-cyan-400',
  grammar:     'text-rose-400',
};

function ImprovedCaption({ caption }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(caption);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-accent-500/20 bg-accent-500/5 p-4 space-y-3 mb-6">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold text-accent-400 uppercase tracking-wider">
          <LightBulbIcon className="w-3.5 h-3.5" />
          Improved Caption (rule-based)
        </h3>
        <button
          onClick={handleCopy}
          className="text-xs text-accent-400 hover:text-accent-300 transition-colors font-medium"
          aria-label="Copy improved caption"
        >
          {copied ? '✓ Copied!' : 'Copy'}
        </button>
      </div>
      <p className="text-sm text-content-main leading-relaxed">{caption}</p>
      <p className="text-[10px] text-content-faint">
        ℹ️ This is a deterministic rule-based rewrite, not an AI generation.
        Passive voice is flagged inline as [consider active voice].
      </p>
    </div>
  );
}

export default function SuggestionsPanel({ suggestions, improvedCaption }) {
  const [filter, setFilter] = useState('all');

  return (
    <div>
      {/* Improved caption */}
      {improvedCaption && (
        <ImprovedCaption caption={improvedCaption} />
      )}

      {/* Suggestion cards */}
      {suggestions?.length > 0 && (
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <h3 className="text-xs font-semibold text-content-muted uppercase tracking-wider mr-1">
              Suggestions ({suggestions.length})
            </h3>
            {['all', ...new Set(suggestions.map((s) => s.category))].map((cat) => (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={clsx(
                  'px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-150 capitalize',
                  filter === cat
                    ? 'bg-primary-600/30 border border-primary-600/50 text-primary-400'
                    : 'bg-surface-700 border border-subtle text-content-faint hover:text-content-main',
                )}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="space-y-2.5">
            {(filter === 'all' ? suggestions : suggestions.filter((s) => s.category === filter)).map((s, i) => {
              const cfg = SEVERITY_CONFIG[s.severity] ?? SEVERITY_CONFIG.low;
              const catColor = CATEGORY_COLORS[s.category] ?? 'text-content-muted';
              return (
                <div
                  key={i}
                  className={clsx(
                    'flex items-start gap-3 p-4 rounded-xl border text-sm animate-fade-in',
                    cfg.bg,
                  )}
                  style={{ animationDelay: `${i * 30}ms` }}
                >
                  <div className="flex-shrink-0 mt-0.5 space-y-1">
                    <span className={clsx('block px-2 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide', cfg.color)}>
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className={clsx('text-[10px] font-semibold uppercase tracking-wide block mb-1', catColor)}>
                      {s.category}
                    </span>
                    <p className="text-content-main leading-relaxed">{s.suggestion}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

import { SparklesIcon, SignalIcon } from '@heroicons/react/24/solid';
import useFileStore from '../../store/fileStore';

/**
 * Application header with branding and backend pre-warm status indicator.
 */
export default function Header() {
  const prewarmStatus = useFileStore((s) => s.prewarmStatus);

  const prewarmLabel = {
    idle: null,
    pinging: { text: 'Connecting to server…', color: 'text-content-muted', dot: 'bg-slate-400 animate-pulse' },
    ready: { text: 'Server ready', color: 'text-success-400', dot: 'bg-success-400' },
    failed: { text: 'Server offline', color: 'text-danger-400', dot: 'bg-danger-400' },
  }[prewarmStatus];

  return (
    <header className="sticky top-0 z-40 glass-strong border-b border-subtle">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-600 to-accent-600 flex items-center justify-center shadow-glow-primary">
              <SparklesIcon className="w-5 h-5 text-content-main" />
            </div>
          </div>
          <div>
            <h1 className="text-sm font-bold text-content-main leading-tight">Content Analyzer</h1>
            <p className="text-xs text-content-faint leading-tight">Social Media Optimizer</p>
          </div>
        </div>

        {/* Server status */}
        {prewarmLabel && (
          <div className={`hidden sm:flex items-center gap-2 text-xs font-medium ${prewarmLabel.color}`}>
            <span className={`w-2 h-2 rounded-full ${prewarmLabel.dot}`} />
            {prewarmLabel.text}
          </div>
        )}

        {/* Right side badge */}
        <div className="flex items-center gap-2">
          <span className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-primary-600/15 border border-primary-600/25 text-primary-400">
            <SignalIcon className="w-3.5 h-3.5" />
            PDF &amp; OCR
          </span>
        </div>
      </div>
    </header>
  );
}

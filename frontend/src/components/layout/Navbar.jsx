import { SparklesIcon, MoonIcon, SunIcon, ClockIcon } from '@heroicons/react/24/outline';
import useFileStore from '../../store/fileStore';
import useThemeStore from '../../store/useThemeStore';
import useHistoryStore from '../../store/useHistoryStore';

/**
 * Application navbar with branding, server pre-warm status, and external links.
 */
export default function Navbar() {
  const prewarmStatus = useFileStore((s) => s.prewarmStatus);
  const { mode, toggleTheme } = useThemeStore();
  const setModalOpen = useHistoryStore((s) => s.setModalOpen);

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
              <SparklesIcon className="w-5 h-5 text-white" />
            </div>
          </div>
          <div>
            <h1 className="text-sm font-bold text-content-main leading-tight">Content Analyzer</h1>
            <p className="text-xs text-content-faint leading-tight">Social Media Optimizer</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Server status indicator */}
          {prewarmLabel && (
            <div className={`hidden sm:flex items-center gap-2 text-xs font-medium mr-2 ${prewarmLabel.color}`}>
              <span className={`w-2 h-2 rounded-full ${prewarmLabel.dot}`} />
              {prewarmLabel.text}
            </div>
          )}

          {/* History Button */}
          <button
            onClick={() => setModalOpen(true)}
            className="btn-ghost !px-2 !py-2"
            title="Upload History"
          >
            <ClockIcon className="w-5 h-5" />
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="btn-ghost !px-2 !py-2"
            title={mode === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
          >
            {mode === 'light' ? <MoonIcon className="w-5 h-5" /> : <SunIcon className="w-5 h-5" />}
          </button>

          {/* GitHub Link */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-content-muted hover:text-content-main transition-colors ml-2"
          >
            GitHub
          </a>
        </div>
      </div>
    </header>
  );
}

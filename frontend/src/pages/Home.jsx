import DropZone from '../components/upload/DropZone';
import FileQueue from '../components/upload/FileQueue';
import ResultPanel from '../components/results/ResultPanel';

export default function Home() {
  return (
    <main className="relative flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-10">
      {/* Hero section */}
      <div className="text-center mb-10 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                        bg-primary-600/15 border border-primary-600/25 text-primary-400 text-xs font-semibold mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse" />
          Stateless · No data stored · Production-ready
        </div>
        <h2 className="text-4xl sm:text-5xl font-extrabold text-content-main mb-3 leading-tight">
          Analyze Your{' '}
          <span className="text-gradient">Social Content</span>
        </h2>
        <p className="text-content-muted text-lg max-w-xl mx-auto">
          Upload PDFs or images — we extract structured text and give you
          actionable engagement insights for any platform.
        </p>
      </div>

      {/* Upload area */}
      <div className="space-y-4">
        <DropZone />
        <FileQueue />
      </div>

      {/* Results */}
      <div className="mt-8">
        <ResultPanel />
      </div>
    </main>
  );
}

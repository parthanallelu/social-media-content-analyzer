export default function Footer() {
  return (
    <footer className="mt-auto border-t border-subtle py-6">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-content-faint">
        <p>
          Social Media Content Analyzer &mdash; Technical Assessment
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <span>React</span>
          <span>&bull;</span>
          <span>Tailwind</span>
          <span>&bull;</span>
          <span>FastAPI</span>
          <span>&bull;</span>
          <span>OpenCV / PyTesseract</span>
          <span>&bull;</span>
          <span>spaCy / NLTK</span>
        </div>
      </div>
    </footer>
  );
}

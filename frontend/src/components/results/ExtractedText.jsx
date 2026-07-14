import clsx from 'clsx';

/**
 * Renders a single structured text block with appropriate HTML element:
 *  - heading → <h1>–<h6>
 *  - bullet   → styled <li>
 *  - paragraph → <p>
 *  - unknown  → <p> with muted style
 */
function TextBlockRenderer({ block }) {
  const { type, level, text } = block;

  if (type === 'heading') {
    const HeadingTag = `h${Math.min(level ?? 2, 6)}`;
    const headingStyles = {
      1: 'text-2xl font-bold text-content-main mt-8 mb-3',
      2: 'text-xl font-bold text-content-main mt-6 mb-2',
      3: 'text-lg font-semibold text-content-main mt-5 mb-2',
      4: 'text-base font-semibold text-content-main mt-4 mb-1',
      5: 'text-sm font-semibold text-content-main mt-3 mb-1 uppercase tracking-wide',
      6: 'text-xs font-semibold text-content-muted mt-3 mb-1 uppercase tracking-wider',
    }[level ?? 2];

    return <HeadingTag className={headingStyles}>{text}</HeadingTag>;
  }

  if (type === 'bullet') {
    return (
      <li className="flex items-start gap-2 text-content-main text-sm leading-relaxed my-1">
        <span className="mt-2 w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0" aria-hidden="true" />
        <span>{text.replace(/^[•\-*–▪◦▸›]\s*/, '')}</span>
      </li>
    );
  }

  if (type === 'paragraph') {
    return <p className="text-content-main text-sm leading-relaxed my-2">{text}</p>;
  }

  // unknown
  return <p className="text-content-faint text-sm font-mono leading-relaxed my-1">{text}</p>;
}

/**
 * ExtractedText — renders the full extraction result in structured form.
 * Groups consecutive bullet blocks into <ul> elements.
 *
 * @param {Object} result - ExtractionResponse from backend
 */
export default function ExtractedText({ result }) {
  if (!result?.content?.blocks?.length) {
    return (
      <p className="text-content-faint text-sm italic py-4">No text blocks were extracted.</p>
    );
  }

  const { blocks } = result.content;

  // Group consecutive bullets into <ul> lists
  const rendered = [];
  let bulletBuffer = [];

  const flushBullets = () => {
    if (bulletBuffer.length > 0) {
      rendered.push(
        <ul key={`ul-${rendered.length}`} className="my-3 pl-1 space-y-0.5">
          {bulletBuffer.map((b, i) => (
            <TextBlockRenderer key={i} block={b} />
          ))}
        </ul>
      );
      bulletBuffer = [];
    }
  };

  blocks.forEach((block, idx) => {
    if (block.type === 'bullet') {
      bulletBuffer.push(block);
    } else {
      flushBullets();
      rendered.push(<TextBlockRenderer key={idx} block={block} />);
    }
  });
  flushBullets();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.metadata.full_text || '');
      // We could add a toast here if we had one
    } catch (err) {
      console.error('Failed to copy text', err);
    }
  };

  const handleDownload = () => {
    const text = result.metadata.full_text || '';
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'extracted_text.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="prose-custom">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between mb-6 pb-4 border-b border-subtle">
        {/* Metadata stats */}
        <div className="flex flex-wrap items-center gap-4">
          <MetaStat label="Pages" value={result.page_count} />
          <MetaStat label="Blocks" value={result.content.blocks.length} />
          <MetaStat label="Characters" value={result.metadata.character_count.toLocaleString()} />
          <MetaStat label="Processed in" value={`${result.metadata.processing_time_ms}ms`} />
          {result.metadata.ocr_confidence !== null && result.metadata.ocr_confidence !== undefined && (
            <MetaStat
              label="OCR Confidence"
              value={`${result.metadata.ocr_confidence.toFixed(1)}%`}
              highlight={result.metadata.ocr_confidence >= 80 ? 'success' : result.metadata.ocr_confidence >= 50 ? 'warning' : 'danger'}
            />
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button onClick={handleCopy} className="btn-ghost" title="Copy to clipboard">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.25.25 0 01-.25.25H9.25a.25.25 0 01-.25-.25v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
            </svg>
            <span className="hidden sm:inline">Copy</span>
          </button>
          <button onClick={handleDownload} className="btn-ghost" title="Download .txt">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            <span className="hidden sm:inline">Download</span>
          </button>
        </div>
      </div>

      {/* Rendered blocks */}
      <div className="max-h-[60vh] overflow-y-auto pr-2 space-y-0">
        {rendered}
      </div>
    </div>
  );
}

function MetaStat({ label, value, highlight }) {
  const valueColor = {
    success: 'text-success-400',
    warning: 'text-warning-400',
    danger: 'text-danger-400',
  }[highlight] ?? 'text-content-main';

  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-content-faint uppercase tracking-wide font-medium">{label}</span>
      <span className={clsx('text-sm font-bold', valueColor)}>{value}</span>
    </div>
  );
}

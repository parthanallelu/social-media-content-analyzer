import { useState } from 'react';

/**
 * Simple tooltip wrapper — shows tooltip text on hover above the child element.
 */
export default function Tooltip({ text, children }) {
  const [visible, setVisible] = useState(false);

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && text && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50
                     px-2.5 py-1.5 text-xs font-medium text-content-main whitespace-nowrap
                     bg-surface-500 border border-subtle rounded-lg shadow-lg
                     animate-fade-in pointer-events-none"
        >
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-surface-500" />
        </div>
      )}
    </div>
  );
}

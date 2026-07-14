import { useState, useRef } from 'react';
import { SparklesIcon, ChartBarIcon, TagIcon, HashtagIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

import Button from '../common/Button';
import ErrorBanner from '../feedback/ErrorBanner';
import LoadingSpinner from '../common/LoadingSpinner';
import { useAnalysis } from '../../hooks/useAnalysis';
import useFileStore from '../../store/fileStore';
import { FILE_STATUS, PLATFORMS } from '../../constants/config';
import { scoreToStrokeColor } from '../../utils/formatters';

import StatisticsCards from './StatisticsCards';
import SuggestionsPanel from './SuggestionsPanel';
import KeywordChart from './KeywordChart';

export default function AnalysisSuggestions({ fileId }) {
  const [platform, setPlatform] = useState('general');
  const [isExporting, setIsExporting] = useState(false);
  const containerRef = useRef(null);
  
  const file = useFileStore((s) => s.files.find((f) => f.id === fileId));
  const { runAnalysis } = useAnalysis(fileId);

  const isAnalyzing = file?.status === FILE_STATUS.ANALYZING;
  const analysis = file?.analysis ?? null;
  const analysisError = file?.analysisError ?? null;

  const handleExportPDF = async () => {
    if (!containerRef.current) return;
    try {
      setIsExporting(true);
      const canvas = await html2canvas(containerRef.current, { 
        scale: 2, 
        useCORS: true,
        onclone: (clonedDoc) => {
          // Force light mode on the cloned document so the PDF is always legible and print-friendly
          clonedDoc.documentElement.removeAttribute('data-theme');
        }
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height]
      });
      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
      pdf.save(`analysis_${file?.name || 'export'}.pdf`);
    } catch (err) {
      console.error('PDF export failed', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Trigger bar */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-surface-600 border border-subtle">
        <SparklesIcon className="w-5 h-5 text-primary-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-content-main">Engagement Analysis</p>
          <p className="text-xs text-content-faint">Rule-based NLP — sentiment, keywords, hashtags, suggestions</p>
        </div>
        
        {analysis && (
          <button
            onClick={handleExportPDF}
            disabled={isExporting || isAnalyzing}
            className="btn-ghost flex items-center gap-1.5"
            title="Export to PDF"
          >
            {isExporting ? <LoadingSpinner label="" /> : <ArrowDownTrayIcon className="w-4 h-4" />}
            <span className="text-xs">PDF</span>
          </button>
        )}

        <select
          id="platform-select"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="text-sm bg-surface-700 border border-subtle rounded-lg px-3 py-2 text-content-main
                     focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/50
                     cursor-pointer transition-colors"
          disabled={isAnalyzing}
          aria-label="Select target platform"
        >
          {PLATFORMS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        <Button
          variant="primary"
          size="sm"
          onClick={() => runAnalysis(platform)}
          loading={isAnalyzing}
          disabled={isAnalyzing}
          id="run-analysis-btn"
        >
          {isAnalyzing ? 'Analyzing…' : analysis ? 'Re-analyze' : 'Run Analysis'}
        </Button>
      </div>

      {/* Non-fatal error */}
      {analysisError && !analysis && (
        <ErrorBanner message={analysisError.message} variant="warning" />
      )}

      {/* Empty / Loading state */}
      {!analysis && !analysisError && !isAnalyzing && (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <ChartBarIcon className="w-12 h-12 text-content-faint" />
          <p className="text-sm text-content-faint">
            Select a platform and click{' '}
            <strong className="text-content-main">Run Analysis</strong>{' '}
            to get tailored engagement suggestions.
          </p>
        </div>
      )}

      {isAnalyzing && !analysis && (
        <div className="py-12">
          <LoadingSpinner label="Analyzing engagement…" />
        </div>
      )}

      {/* Results */}
      {analysis && (
        <div ref={containerRef} className="space-y-6 animate-slide-up relative">
          {isAnalyzing && (
            <div className="absolute inset-0 z-10 bg-surface-900 backdrop-blur-sm rounded-xl flex items-center justify-center">
              <LoadingSpinner label="Re-analyzing…" />
            </div>
          )}

          {/* Statistics bar */}
          {analysis.statistics && <StatisticsCards stats={analysis.statistics} />}

          {/* Sentiment */}
          {analysis.sentiment && <SentimentCard sentiment={analysis.sentiment} />}

          {/* Score rings */}
          <ScoreSection score={analysis.score} />

          {/* Keywords + hashtags */}
          {(analysis.keywords?.length > 0 || analysis.suggested_hashtags?.length > 0) && (
            <KeywordsHashtags
              keywords={analysis.keywords}
              hashtags={analysis.suggested_hashtags}
            />
          )}

          {/* Suggestion cards + Improved caption */}
          <SuggestionsPanel 
            suggestions={analysis.suggestions} 
            improvedCaption={analysis.improved_caption}
          />
        </div>
      )}
    </div>
  );
}

// ── Sentiment ──────────────────────────────────────────────────────────────────

const SENTIMENT_COLOR = {
  'very positive': 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  'positive':      'text-success-400 border-success-500/30 bg-success-500/10',
  'neutral':       'text-content-muted border-slate-500/30 bg-slate-500/10',
  'negative':      'text-warning-400 border-warning-500/30 bg-warning-500/10',
  'very negative': 'text-danger-400 border-danger-500/30 bg-danger-500/10',
};

const SENTIMENT_EMOJI = {
  'very positive': '😄',
  'positive':      '🙂',
  'neutral':       '😐',
  'negative':      '🙁',
  'very negative': '😟',
};

function SentimentCard({ sentiment }) {
  const colorClass = SENTIMENT_COLOR[sentiment.label] ?? SENTIMENT_COLOR.neutral;
  const emoji = SENTIMENT_EMOJI[sentiment.label] ?? '😐';

  return (
    <div className={clsx('flex flex-wrap items-center gap-4 p-4 rounded-xl border', colorClass)}>
      <span className="text-2xl" role="img" aria-label={sentiment.label}>{emoji}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-content-main capitalize">
          Tone: {sentiment.label}{' '}
          <span className="text-xs font-normal text-content-muted">· {sentiment.subjectivity_label}</span>
        </p>
        <div className="flex items-center gap-4 mt-1">
          <MeterBar
            label="Polarity"
            value={(sentiment.polarity + 1) / 2} // normalise -1→1 to 0→1
            displayValue={sentiment.polarity.toFixed(2)}
            color="#34d399"
          />
          <MeterBar
            label="Subjectivity"
            value={sentiment.subjectivity}
            displayValue={sentiment.subjectivity.toFixed(2)}
            color="#a78bfa"
          />
        </div>
      </div>
    </div>
  );
}

function MeterBar({ label, value, displayValue, color }) {
  return (
    <div className="flex-1 min-w-[100px]">
      <div className="flex justify-between text-xs text-content-faint mb-1">
        <span>{label}</span>
        <span className="font-medium" style={{ color }}>{displayValue}</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.round(value * 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ── Score rings ────────────────────────────────────────────────────────────────

function ScoreSection({ score }) {
  const metrics = [
    { label: 'Overall',     value: score.overall,     size: 'lg' },
    { label: 'Readability', value: score.readability,  size: 'sm' },
    { label: 'Engagement',  value: score.engagement,   size: 'sm' },
    { label: 'Structure',   value: score.structure,    size: 'sm' },
  ];

  return (
    <div className="flex flex-wrap items-center justify-around gap-6 p-5 rounded-xl bg-surface-700 border border-subtle">
      {metrics.map((m) => (
        <ScoreRing key={m.label} label={m.label} value={m.value} large={m.size === 'lg'} />
      ))}
    </div>
  );
}

function ScoreRing({ label, value, large = false }) {
  const r             = large ? 38 : 28;
  const circumference = 2 * Math.PI * r;
  const offset        = circumference - (value / 100) * circumference;
  const strokeColor   = scoreToStrokeColor(value);
  const size          = large ? 100 : 76;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-label={`${label}: ${value}/100`}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={large ? 6 : 5} />
        <circle
          cx={size/2} cy={size/2} r={r}
          fill="none" stroke={strokeColor}
          strokeWidth={large ? 6 : 5} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          transform={`rotate(-90 ${size/2} ${size/2})`}
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
        <text
          x={size/2} y={size/2}
          textAnchor="middle" dominantBaseline="central"
          fill={strokeColor} fontSize={large ? 20 : 14}
          fontWeight="700" fontFamily="Inter, sans-serif"
        >
          {value}
        </text>
      </svg>
      <span className="text-xs text-content-faint font-medium">{label}</span>
    </div>
  );
}

// ── Keywords + hashtags ────────────────────────────────────────────────────────

function KeywordsHashtags({ keywords, hashtags }) {
  const [copied, setCopied] = useState(false);

  const handleCopyHashtags = async () => {
    if (!hashtags?.length) return;
    await navigator.clipboard.writeText(hashtags.join(' '));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* Keywords Chart */}
      {keywords?.length > 0 && (
        <div className="bg-surface-700 p-4 rounded-xl border border-subtle">
          <KeywordChart keywords={keywords} />
        </div>
      )}

      {/* Hashtags */}
      {hashtags?.length > 0 && (
        <div className="bg-surface-700 p-4 rounded-xl border border-subtle">
          <div className="flex items-center justify-between mb-4">
            <h3 className="flex items-center gap-1.5 text-xs font-semibold text-content-muted uppercase tracking-wider">
              <HashtagIcon className="w-3.5 h-3.5" />
              Suggested Hashtags
            </h3>
            <button
              onClick={handleCopyHashtags}
              className="text-xs text-primary-600 hover:text-primary-700 transition-colors font-medium"
              aria-label="Copy all hashtags"
            >
              {copied ? '✓ Copied!' : 'Copy all'}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {hashtags.map((tag) => (
              <span
                key={tag}
                className="px-2.5 py-1 rounded-full text-xs font-medium
                           bg-primary-600/10 border border-primary-600/20 text-primary-600
                           hover:bg-primary-600/20 transition-colors cursor-default"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KeywordPill({ kw }) {
  const opacity = 0.4 + kw.score * 0.6; // scale opacity 0.4→1.0 by score
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                 bg-surface-600 border border-subtle text-content-main"
      style={{ opacity }}
      title={`Freq: ${kw.frequency} · Score: ${(kw.score * 100).toFixed(0)}% · ${kw.pos_tag}`}
    >
      {kw.word}
      <span className="text-[10px] text-content-faint font-bold">×{kw.frequency}</span>
    </span>
  );
}


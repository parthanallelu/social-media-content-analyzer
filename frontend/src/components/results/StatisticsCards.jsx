import { DocumentTextIcon, ClockIcon, CheckCircleIcon, ExclamationCircleIcon, HashtagIcon, FaceSmileIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

export default function StatisticsCards({ stats }) {
  const items = [
    {
      Icon: DocumentTextIcon,
      label: 'Words',
      value: stats.word_count?.toLocaleString(),
    },
    {
      Icon: ClockIcon,
      label: 'Read time',
      value: stats.reading_time_label,
    },
    {
      Icon: CheckCircleIcon,
      label: 'CTA',
      value: stats.cta_detected ? 'Yes ✓' : 'No ✗',
      color: stats.cta_detected ? 'text-success-400' : 'text-danger-400',
    },
    {
      Icon: ExclamationCircleIcon,
      label: 'Questions',
      value: stats.question_count,
    },
    {
      Icon: HashtagIcon,
      label: 'Hashtags',
      value: stats.hashtag_count,
    },
    {
      Icon: FaceSmileIcon,
      label: 'Emojis',
      value: stats.emoji_count,
    },
  ];

  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
      {items.map(({ Icon, label, value, color }) => (
        <div
          key={label}
          className="flex flex-col items-center gap-1 py-3 rounded-xl bg-surface-700 border border-subtle"
        >
          <Icon className="w-4 h-4 text-content-faint" />
          <span className={clsx('text-sm font-bold', color ?? 'text-content-main')}>{value}</span>
          <span className="text-[10px] text-content-faint uppercase tracking-wider">{label}</span>
        </div>
      ))}
    </div>
  );
}

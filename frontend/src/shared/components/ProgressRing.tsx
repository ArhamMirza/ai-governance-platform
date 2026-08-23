interface ProgressRingProps {
  value: number;
  total: number;
  label: string;
  caption?: string;
}

const SIZE = 92;
const STROKE = 9;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Coverage ratio as a ring. Renders an empty ring rather than dividing by zero. */
export function ProgressRing({ value, total, label, caption }: ProgressRingProps) {
  const ratio = total > 0 ? Math.min(1, value / total) : 0;
  const percent = Math.round(ratio * 100);

  return (
    <div className="progress-ring">
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img"
        aria-label={`${label}: ${value} of ${total} (${percent}%)`}>
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE}
          className="progress-ring-track"
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE}
          strokeLinecap="round"
          className="progress-ring-value"
          strokeDasharray={`${CIRCUMFERENCE * ratio} ${CIRCUMFERENCE}`}
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        />
        <text x="50%" y="50%" className="progress-ring-text" textAnchor="middle" dy="0.36em">
          {percent}%
        </text>
      </svg>
      <div className="progress-ring-meta">
        <div className="progress-ring-label">{label}</div>
        <div className="progress-ring-caption">{caption ?? `${value} of ${total}`}</div>
      </div>
    </div>
  );
}

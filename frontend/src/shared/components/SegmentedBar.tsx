export interface Segment {
  key: string;
  label: string;
  value: number;
  tone: "high" | "medium" | "low" | "neutral" | "primary" | "success" | "warning";
}

interface SegmentedBarProps {
  segments: Segment[];
  emptyLabel?: string;
}

/**
 * A single proportional bar plus a legend. Segments with a zero value keep
 * their legend entry (so the reader sees the category exists) but take no bar
 * width.
 */
export function SegmentedBar({ segments, emptyLabel = "No data yet." }: SegmentedBarProps) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);

  if (total === 0) return <p className="chart-empty">{emptyLabel}</p>;

  return (
    <div className="segmented-bar">
      <div className="segmented-bar-track" role="img" aria-label={
        segments.map((s) => `${s.label}: ${s.value}`).join(", ")
      }>
        {segments
          .filter((segment) => segment.value > 0)
          .map((segment) => (
            <div
              key={segment.key}
              className="segmented-bar-fill"
              data-tone={segment.tone}
              style={{ width: `${(segment.value / total) * 100}%` }}
            />
          ))}
      </div>
      <ul className="segmented-bar-legend">
        {segments.map((segment) => (
          <li key={segment.key}>
            <span className="legend-dot" data-tone={segment.tone} />
            <span className="legend-label">{segment.label}</span>
            <span className="legend-value">{segment.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

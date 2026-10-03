import { formatValue, targetLabel } from "../labels";
import type { Measurement, TargetDirection } from "../types";

interface ObjectiveTrendChartProps {
  measurements: Measurement[];
  direction: TargetDirection;
  target: number;
  baseline: number | null;
  unit: string | null;
}

const WIDTH = 560;
const HEIGHT = 200;
const MARGIN = { top: 18, right: 96, bottom: 28, left: 48 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;

const dayNumber = (iso: string) => Date.parse(`${iso}T00:00:00Z`) / 86_400_000;

/** Readings over time against the target -- a dashed line, with each
 * reading's dot coloured by whether it met it. Hand-drawn SVG; the project
 * has no chart library. */
export function ObjectiveTrendChart({
  measurements,
  direction,
  target,
  baseline,
  unit,
}: ObjectiveTrendChartProps) {
  // Oldest first; of two the same day, the later-recorded one plots last.
  const points = [...measurements].sort(
    (a, b) => a.measured_on.localeCompare(b.measured_on) || a.id - b.id,
  );
  if (points.length === 0) return null;

  const values = [...points.map((p) => p.value), target, ...(baseline === null ? [] : [baseline])];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const pad = (high - low || Math.abs(high) || 1) * 0.12;
  const yMin = low - pad;
  const yMax = high + pad;
  const y = (value: number) => MARGIN.top + PLOT_H - ((value - yMin) / (yMax - yMin)) * PLOT_H;

  const firstDay = dayNumber(points[0].measured_on);
  const span = dayNumber(points[points.length - 1].measured_on) - firstDay;
  const x = (iso: string) =>
    MARGIN.left + (span === 0 ? PLOT_W / 2 : ((dayNumber(iso) - firstDay) / span) * PLOT_W);

  const meets = (value: number) => (direction === "at_least" ? value >= target : value <= target);
  const ticks = [yMin + pad, (yMin + yMax) / 2, yMax - pad];

  return (
    <svg
      className="objective-chart"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Readings against the target of ${targetLabel(direction, target, unit)}`}
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line
            className="objective-chart-grid"
            x1={MARGIN.left}
            x2={MARGIN.left + PLOT_W}
            y1={y(tick)}
            y2={y(tick)}
          />
          <text className="objective-chart-axis" x={MARGIN.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">
            {formatValue(Number(tick.toFixed(1)), unit)}
          </text>
        </g>
      ))}

      {baseline !== null && (
        <g>
          <line
            className="objective-chart-baseline"
            x1={MARGIN.left}
            x2={MARGIN.left + PLOT_W}
            y1={y(baseline)}
            y2={y(baseline)}
          />
          <text className="objective-chart-axis" x={MARGIN.left + PLOT_W + 8} y={y(baseline)} dominantBaseline="middle">
            Baseline
          </text>
        </g>
      )}

      <line
        className="objective-chart-target"
        x1={MARGIN.left}
        x2={MARGIN.left + PLOT_W}
        y1={y(target)}
        y2={y(target)}
      />
      <text className="objective-chart-target-label" x={MARGIN.left + PLOT_W + 8} y={y(target)} dominantBaseline="middle">
        Target {targetLabel(direction, target, unit)}
      </text>

      {points.length > 1 && (
        <polyline
          className="objective-chart-line"
          points={points.map((p) => `${x(p.measured_on)},${y(p.value)}`).join(" ")}
        />
      )}
      {points.map((p) => (
        <circle
          key={p.id}
          className="objective-chart-dot"
          data-meets={meets(p.value)}
          cx={x(p.measured_on)}
          cy={y(p.value)}
          r={4.5}
        >
          <title>{`${p.measured_on}: ${formatValue(p.value, unit)}`}</title>
        </circle>
      ))}

      <text className="objective-chart-axis" x={MARGIN.left} y={HEIGHT - 8}>
        {points[0].measured_on}
      </text>
      {points.length > 1 && (
        <text className="objective-chart-axis" x={MARGIN.left + PLOT_W} y={HEIGHT - 8} textAnchor="end">
          {points[points.length - 1].measured_on}
        </text>
      )}
    </svg>
  );
}

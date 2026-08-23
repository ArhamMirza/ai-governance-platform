import type { SheetRow } from "../../sheets/types";
import { type Bands, DEFAULT_BANDS, severityForScore } from "../riskSeverity";

export interface MatrixCell {
  likelihood: number;
  impact: number;
  count: number;
}

interface RiskMatrixProps {
  /** Raw rows to aggregate client-side (detail page). */
  rows?: SheetRow[];
  /** Pre-aggregated cells from a summary endpoint (dashboard, portfolio). */
  cells?: MatrixCell[];
  /** Severity bands to shade with; defaults to the built-in bands. */
  bands?: Bands;
  caption?: string;
}

const LEVELS = [1, 2, 3, 4, 5];

function toLevel(value: unknown): number | null {
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return null;
  return Math.min(5, Math.max(1, Math.round(num)));
}

function countsFrom(rows: SheetRow[], cells: MatrixCell[]): Map<string, number> {
  const counts = new Map<string, number>();

  for (const cell of cells) {
    counts.set(`${cell.likelihood}-${cell.impact}`, cell.count);
  }

  for (const row of rows) {
    const likelihood = toLevel(row.data.likelihood);
    const impact = toLevel(row.data.impact);
    if (likelihood === null || impact === null) continue;
    const key = `${likelihood}-${impact}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return counts;
}

export function RiskMatrix({
  rows = [],
  cells = [],
  bands = DEFAULT_BANDS,
  caption = "Risk Matrix (Likelihood × Impact)",
}: RiskMatrixProps) {
  const counts = countsFrom(rows, cells);

  return (
    <table className="risk-matrix" aria-label="Risk matrix">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th>Likelihood \ Impact</th>
          {LEVELS.map((impact) => (
            <th key={impact}>{impact}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {[...LEVELS].reverse().map((likelihood) => (
          <tr key={likelihood}>
            <th>{likelihood}</th>
            {LEVELS.map((impact) => {
              const score = likelihood * impact;
              const count = counts.get(`${likelihood}-${impact}`) ?? 0;
              return (
                <td
                  key={impact}
                  aria-label={`Likelihood ${likelihood}, Impact ${impact}, ${count} risk(s)`}
                  data-severity={severityForScore(score, bands)}
                  data-empty={count === 0 ? "true" : undefined}
                >
                  {count > 0 ? count : ""}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

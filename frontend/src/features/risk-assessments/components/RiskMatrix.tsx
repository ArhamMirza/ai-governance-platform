import type { SheetRow } from "../../sheets/types";

interface RiskMatrixProps {
  rows: SheetRow[];
}

const LEVELS = [1, 2, 3, 4, 5];

function toLevel(value: unknown): number | null {
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return null;
  return Math.min(5, Math.max(1, Math.round(num)));
}

function scoreColor(score: number): string {
  if (score <= 4) return "#c6efce";
  if (score <= 12) return "#ffeb9c";
  return "#ffc7ce";
}

export function RiskMatrix({ rows }: RiskMatrixProps) {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const likelihood = toLevel(row.data.likelihood);
    const impact = toLevel(row.data.impact);
    if (likelihood === null || impact === null) continue;
    const key = `${likelihood}-${impact}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return (
    <table aria-label="Risk matrix">
      <caption>Risk Matrix (Likelihood × Impact)</caption>
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
                  style={{ backgroundColor: scoreColor(score) }}
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

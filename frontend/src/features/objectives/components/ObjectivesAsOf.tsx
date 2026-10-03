import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useObjectivesAsOf } from "../hooks";
import { formatValue, targetLabel } from "../labels";

/** Every AI objective as it stood on a meeting's date -- ISO/IEC 42001 9.3
 * asks management review to consider their achievement. Computed from the
 * readings recorded by then, so a past meeting keeps showing what it
 * reviewed. */
export function ObjectivesAsOf({ asOf }: { asOf: string }) {
  const { data: objectives, isLoading, isError } = useObjectivesAsOf(asOf);

  return (
    <section>
      <h3>AI objectives as of {asOf}</h3>
      {isLoading ? (
        <p>Loading objectives...</p>
      ) : isError ? (
        <p>Failed to load objectives.</p>
      ) : !objectives || objectives.length === 0 ? (
        <p>No AI objectives had been set by this date.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Objective</th>
              <th>Standing</th>
              <th>Latest by then</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {objectives.map((objective) => (
              <tr key={objective.id}>
                <td>
                  <Link to={`/objectives/${objective.id}`}>{objective.title}</Link>
                  {objective.standing.measurement_overdue && (
                    <span className="flag-chip">Measurement overdue</span>
                  )}
                </td>
                <td>
                  <StatusBadge status={objective.standing.state} />
                </td>
                <td data-type="number">
                  {objective.standing.latest_value === null
                    ? "—"
                    : `${formatValue(objective.standing.latest_value, objective.unit)} (${objective.standing.latest_on})`}
                </td>
                <td data-type="number">
                  {objective.kind === "milestone"
                    ? `Milestone by ${objective.target_date}`
                    : targetLabel(objective.direction, objective.target_value, objective.unit)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

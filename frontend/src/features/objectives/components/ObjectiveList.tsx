import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useObjectives } from "../hooks";
import { formatValue, isFlagged, targetLabel } from "../labels";
import type { Objective } from "../types";

/** The chips an objective carries wherever it's listed. */
export function ObjectiveFlags({ objective }: { objective: Objective }) {
  return objective.standing.measurement_overdue ? (
    <span className="flag-chip">Measurement overdue</span>
  ) : null;
}

export function ObjectiveList() {
  const { data: objectives, isLoading, isError } = useObjectives();

  if (isLoading) return <p>Loading objectives...</p>;
  if (isError) return <p>Failed to load objectives.</p>;
  if (!objectives || objectives.length === 0) {
    return <p>No AI objectives yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Objective</th>
          <th>Standing</th>
          <th>Latest</th>
          <th>Target</th>
          <th>Target date</th>
        </tr>
      </thead>
      <tbody>
        {objectives.map((objective) => (
          <tr key={objective.id} className={isFlagged(objective) ? "row-flagged" : undefined}>
            <td>
              <Link to={`/objectives/${objective.id}`}>{objective.title}</Link>
              <ObjectiveFlags objective={objective} />
            </td>
            <td>
              <StatusBadge status={objective.standing.state} />
            </td>
            <td data-type="number">
              {objective.standing.latest_value === null
                ? "—"
                : formatValue(objective.standing.latest_value, objective.unit)}
            </td>
            <td data-type="number">
              {objective.kind === "milestone"
                ? "Milestone"
                : targetLabel(objective.direction, objective.target_value, objective.unit)}
            </td>
            <td data-type="date">{objective.target_date ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

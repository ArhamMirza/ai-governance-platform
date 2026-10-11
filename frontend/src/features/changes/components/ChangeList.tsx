import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useChanges } from "../hooks";
import { changeTypeLabel, isFlagged } from "../labels";
import type { Change } from "../types";

/** The chip a change carries wherever it's listed. */
export function ChangeFlags({ change }: { change: Change }) {
  return change.standing.overdue ? <span className="flag-chip">Overdue</span> : null;
}

export function ChangeList() {
  const { data: changes, isLoading, isError } = useChanges();

  if (isLoading) return <p>Loading changes...</p>;
  if (isError) return <p>Failed to load changes.</p>;
  if (!changes || changes.length === 0) {
    return <p>No planned changes yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Change</th>
          <th>Affects</th>
          <th>Status</th>
          <th>Planned for</th>
        </tr>
      </thead>
      <tbody>
        {changes.map((change) => (
          <tr key={change.id} className={isFlagged(change) ? "row-flagged" : undefined}>
            <td>
              <Link to={`/changes/${change.id}`}>{change.title}</Link>
              <ChangeFlags change={change} />
            </td>
            <td>{changeTypeLabel(change.change_type)}</td>
            <td>
              <StatusBadge status={change.standing.state} />
            </td>
            <td data-type="date">{change.planned_date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

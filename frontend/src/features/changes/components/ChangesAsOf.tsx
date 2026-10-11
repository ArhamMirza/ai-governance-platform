import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useChangesAsOf } from "../hooks";
import { changeTypeLabel } from "../labels";

/** Every planned change as it stood on a meeting's date -- ISO/IEC 42001 6.3
 * has changes planned and reviewed. Computed from the dates recorded by
 * then, so a past meeting keeps showing what it reviewed. */
export function ChangesAsOf({ asOf }: { asOf: string }) {
  const { data: changes, isLoading, isError } = useChangesAsOf(asOf);

  return (
    <section>
      <h3>Planned changes as of {asOf}</h3>
      {isLoading ? (
        <p>Loading changes...</p>
      ) : isError ? (
        <p>Failed to load changes.</p>
      ) : !changes || changes.length === 0 ? (
        <p>No changes had been raised by this date.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Change</th>
              <th>Affects</th>
              <th>Status then</th>
              <th>Planned for</th>
            </tr>
          </thead>
          <tbody>
            {changes.map((change) => (
              <tr key={change.id}>
                <td>
                  <Link to={`/changes/${change.id}`}>{change.title}</Link>
                  {change.standing.overdue && <span className="flag-chip">Overdue</span>}
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
      )}
    </section>
  );
}

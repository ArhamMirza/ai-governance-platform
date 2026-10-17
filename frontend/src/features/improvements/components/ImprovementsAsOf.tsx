import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useImprovementsAsOf } from "../hooks";
import { sourceLabel } from "../labels";

/** Every improvement as it stood on a meeting's date -- ISO/IEC 42001 9.3
 * reviews opportunities for continual improvement (10.1). Computed from the
 * dates recorded by then, so a past meeting keeps showing what it reviewed. */
export function ImprovementsAsOf({ asOf }: { asOf: string }) {
  const { data: improvements, isLoading, isError } = useImprovementsAsOf(asOf);

  return (
    <section>
      <h3>Improvements as of {asOf}</h3>
      {isLoading ? (
        <p>Loading improvements...</p>
      ) : isError ? (
        <p>Failed to load improvements.</p>
      ) : !improvements || improvements.length === 0 ? (
        <p>No improvements had been raised by this date.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Improvement</th>
              <th>Came from</th>
              <th>Status then</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {improvements.map((improvement) => (
              <tr key={improvement.id}>
                <td>
                  <Link to={`/improvements/${improvement.id}`}>{improvement.title}</Link>
                  {improvement.standing.overdue && <span className="flag-chip">Overdue</span>}
                </td>
                <td>{sourceLabel(improvement.source)}</td>
                <td>
                  <StatusBadge status={improvement.standing.state} />
                </td>
                <td data-type="date">{improvement.target_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

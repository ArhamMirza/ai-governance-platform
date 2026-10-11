import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useCommunications } from "../hooks";
import { cadenceLabel, directionLabel } from "../labels";

export function CommunicationList() {
  const { data: items, isLoading, isError } = useCommunications();

  if (isLoading) return <p>Loading the communication plan...</p>;
  if (isError) return <p>Failed to load the communication plan.</p>;
  if (!items || items.length === 0) {
    return <p>Nothing planned yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Communication</th>
          <th>Audience</th>
          <th>How often</th>
          <th>Last done</th>
          <th>Next due</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} className={item.overdue ? "row-flagged" : undefined}>
            <td>
              <Link to={`/communications/${item.id}`}>{item.topic}</Link>
              {item.overdue && <span className="flag-chip">Overdue</span>}
              {item.status === "retired" && <StatusBadge status="retired" />}
              <span className="approval-note"> {directionLabel(item.direction)}</span>
            </td>
            <td>{item.audience}</td>
            <td>{cadenceLabel(item)}</td>
            <td data-type="date">{item.last_communicated_on ?? "—"}</td>
            <td data-type="date">{item.next_due ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

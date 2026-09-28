import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useIncidents } from "../hooks";
import { aiSystemName } from "../labels";

export function IncidentList() {
  const { data: incidents, isLoading, isError } = useIncidents();
  const { data: inventory } = useAISystemInventoryRows();

  if (isLoading) return <p>Loading incidents...</p>;
  if (isError) return <p>Failed to load incidents.</p>;
  if (!incidents || incidents.length === 0) {
    return <p>No incidents logged.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>AI system</th>
          <th>Detected</th>
          <th>Severity</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {incidents.map((incident) => {
          const systemId = incident.ai_system_row_id;
          return (
            <tr key={incident.id} className={incident.reporting_overdue ? "row-flagged" : undefined}>
              <td>
                <Link to={`/incidents/${incident.id}`}>{incident.title}</Link>
                {incident.is_serious && <span className="flag-chip">Serious</span>}
                {incident.reporting_overdue && <span className="flag-chip">Report overdue</span>}
              </td>
              <td>
                {systemId === null
                  ? "—"
                  : aiSystemName(
                      inventory?.rows.find((row) => row.id === systemId),
                      systemId,
                    )}
              </td>
              <td data-type="date">{incident.detected_on}</td>
              <td>{incident.severity}</td>
              <td>
                <StatusBadge status={incident.status} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

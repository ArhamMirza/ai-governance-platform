import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAuditPrograms } from "../hooks";

export function AuditProgramList() {
  const { data: programs, isLoading, isError } = useAuditPrograms();

  if (isLoading) return <p>Loading audit programs...</p>;
  if (isError) return <p>Failed to load audit programs.</p>;
  if (!programs || programs.length === 0) return <p>No audit programs yet.</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Schedule</th>
          <th>Next due</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {programs.map((program) => (
          <tr key={program.id} className={program.overdue ? "row-flagged" : undefined}>
            <td>
              <Link to={`/audit-programs/${program.id}`}>{program.title}</Link>
            </td>
            <td>
              {program.schedule_type === "interval"
                ? `Every ${program.interval_months} month(s)`
                : "Ad hoc"}
            </td>
            <td data-type="date">
              {program.next_due_date ?? "—"}
              {program.overdue && <span className="flag-chip">Overdue</span>}
            </td>
            <td>
              <StatusBadge status={program.status} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

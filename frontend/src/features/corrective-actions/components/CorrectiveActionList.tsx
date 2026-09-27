import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCorrectiveActions } from "../hooks";

export function CorrectiveActionList() {
  const { data: correctiveActions, isLoading, isError } = useCorrectiveActions();
  const { data: directory } = useUserDirectory();

  if (isLoading) return <p>Loading corrective actions...</p>;
  if (isError) return <p>Failed to load corrective actions.</p>;
  if (!correctiveActions || correctiveActions.length === 0) {
    return <p>No corrective actions yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Assignee</th>
          <th>Due date</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {correctiveActions.map((correctiveAction) => {
          const assignee = directory?.find((user) => user.id === correctiveAction.assignee_id);
          return (
            <tr key={correctiveAction.id} className={correctiveAction.overdue ? "row-flagged" : undefined}>
              <td>
                <Link to={`/corrective-actions/${correctiveAction.id}`}>
                  {correctiveAction.title}
                </Link>
              </td>
              <td>{assignee ? formatUserOption(assignee) : "Unassigned"}</td>
              <td data-type="date">
                {correctiveAction.due_date}
                {correctiveAction.overdue && <span className="flag-chip">Overdue</span>}
              </td>
              <td>
                <StatusBadge status={correctiveAction.status} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

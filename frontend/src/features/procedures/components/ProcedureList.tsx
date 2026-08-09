import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useProcedures } from "../hooks";

export function ProcedureList() {
  const { data: procedures, isLoading, isError } = useProcedures();

  if (isLoading) return <p>Loading procedures...</p>;
  if (isError) return <p>Failed to load procedures.</p>;
  if (!procedures || procedures.length === 0) return <p>No procedures yet.</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Status</th>
          <th>Version</th>
        </tr>
      </thead>
      <tbody>
        {procedures.map((procedure) => (
          <tr key={procedure.id}>
            <td>
              <Link to={`/procedures/${procedure.id}`}>{procedure.title}</Link>
            </td>
            <td>
              <StatusBadge status={procedure.status} />
            </td>
            <td>{procedure.version}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

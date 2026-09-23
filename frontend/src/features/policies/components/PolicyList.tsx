import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { usePolicies } from "../hooks";

export function PolicyList() {
  const { data: policies, isLoading, isError } = usePolicies();

  if (isLoading) return <p>Loading policies...</p>;
  if (isError) return <p>Failed to load policies.</p>;
  if (!policies || policies.length === 0) return <p>No policies yet.</p>;

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
        {policies.map((policy) => (
          <tr key={policy.id}>
            <td>
              <Link to={`/policies/${policy.id}`}>{policy.title}</Link>
            </td>
            <td>
              <StatusBadge status={policy.status} />
            </td>
            <td data-type="number">{policy.version}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

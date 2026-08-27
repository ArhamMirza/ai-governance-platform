import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { useCurrentUser } from "../../auth/hooks";
import { useUpdateUser, useUsers } from "../hooks";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  contributor: "Contributor",
  viewer: "Viewer",
};

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

export function UsersList() {
  const { data: users, isLoading, isError } = useUsers();
  const { data: me } = useCurrentUser();
  const updateUser = useUpdateUser();
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading users...</p>;
  if (isError || !users) return <p>Failed to load users.</p>;

  const handleRoleChange = async (userId: number, role: string) => {
    setError(null);
    try {
      await updateUser.mutateAsync({ id: userId, data: { role } });
    } catch (err) {
      setError(readError(err, "Failed to update role"));
    }
  };

  const handleToggleActive = async (userId: number, isActive: boolean) => {
    setError(null);
    try {
      await updateUser.mutateAsync({ id: userId, data: { is_active: !isActive } });
    } catch (err) {
      setError(readError(err, "Failed to update status"));
    }
  };

  return (
    <div>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isSelf = user.id === me?.id;
            return (
              <tr key={user.id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  {isSelf ? (
                    ROLE_LABELS[user.role] ?? user.role
                  ) : (
                    <select
                      aria-label={`Role for ${user.name}`}
                      value={user.role}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      disabled={updateUser.isPending}
                    >
                      <option value="viewer">Viewer</option>
                      <option value="contributor">Contributor</option>
                      <option value="admin">Admin</option>
                    </select>
                  )}
                </td>
                <td>
                  <span
                    className="status-badge"
                    data-status={user.is_active ? "approved" : "retired"}
                  >
                    {user.is_active ? "Active" : "Deactivated"}
                  </span>
                </td>
                <td>
                  {!isSelf && (
                    <button
                      onClick={() => handleToggleActive(user.id, user.is_active)}
                      disabled={updateUser.isPending}
                    >
                      {user.is_active ? "Deactivate" : "Reactivate"}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

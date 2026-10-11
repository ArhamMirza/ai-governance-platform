import { useState } from "react";

import { ConfirmDialog } from "../../../shared/components/ConfirmDialog";
import { readError } from "../../../shared/api/readError";
import { useCurrentUser } from "../../auth/hooks";
import { useUpdateUser, useUserAccountabilities, useUsers } from "../hooks";
import type { ManagedUser, UserAccountabilities } from "../types";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  contributor: "Contributor",
  viewer: "Viewer",
  employee: "Employee",
};

/** Nobody may approve in a deactivated owner's place, so whatever they hold
 * is stuck until it is reassigned. Say so before the act, not after. */
function accountabilityWarning(report: UserAccountabilities | undefined): string {
  if (!report) return "Checking what this person is accountable for...";

  const holdings = [
    report.governance_roles.length &&
      `${report.governance_roles.join(", ")} (governance role${report.governance_roles.length === 1 ? "" : "s"})`,
    report.ai_systems_owned.length && `owner of ${report.ai_systems_owned.join(", ")}`,
    report.datasets_owned.length && `Data Owner for ${report.datasets_owned.join(", ")}`,
    report.open_risk_items && `${report.open_risk_items} open risk item(s)`,
  ].filter(Boolean) as string[];

  if (holdings.length === 0) {
    return "They lose access immediately. They hold nothing that needs reassigning.";
  }
  return `They lose access immediately, and nobody can approve in their place. Reassign these first or they will be stuck: ${holdings.join("; ")}.`;
}

export function UsersList() {
  const { data: users, isLoading, isError } = useUsers();
  const { data: me } = useCurrentUser();
  const updateUser = useUpdateUser();
  const [error, setError] = useState<string | null>(null);
  const [confirmingDeactivation, setConfirmingDeactivation] = useState<ManagedUser | null>(null);
  const { data: accountabilities } = useUserAccountabilities(
    confirmingDeactivation?.id ?? null,
  );

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

  const setActive = async (userId: number, isActive: boolean) => {
    setError(null);
    try {
      await updateUser.mutateAsync({ id: userId, data: { is_active: isActive } });
      setConfirmingDeactivation(null);
    } catch (err) {
      setError(readError(err, "Failed to update status"));
    }
  };

  return (
    <div>
      {/* While the dialog is open it shows the error itself -- rendering it
          here too would duplicate it, and behind the modal backdrop. */}
      {error && !confirmingDeactivation && <p role="alert">{error}</p>}
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
                      <option value="employee">Employee</option>
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
                      onClick={() =>
                        user.is_active
                          ? setConfirmingDeactivation(user)
                          : setActive(user.id, true)
                      }
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

      {confirmingDeactivation && (
        <ConfirmDialog
          title={`Deactivate ${confirmingDeactivation.name}?`}
          message={accountabilityWarning(accountabilities)}
          confirmLabel="Deactivate"
          pendingLabel="Deactivating..."
          isPending={updateUser.isPending}
          error={error}
          onConfirm={() => setActive(confirmingDeactivation.id, false)}
          onCancel={() => setConfirmingDeactivation(null)}
        />
      )}
    </div>
  );
}

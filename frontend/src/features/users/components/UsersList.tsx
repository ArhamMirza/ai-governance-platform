import { useState } from "react";

import { ConfirmDialog } from "../../../shared/components/ConfirmDialog";
import { readError } from "../../../shared/api/readError";
import { useCurrentUser } from "../../auth/hooks";
import { useResetPassword, useUpdateUser, useUserAccountabilities, useUsers } from "../hooks";
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
  const resetPassword = useResetPassword();
  const [error, setError] = useState<string | null>(null);
  const [confirmingDeactivation, setConfirmingDeactivation] = useState<ManagedUser | null>(null);
  const [confirmingReset, setConfirmingReset] = useState<ManagedUser | null>(null);
  // Held in state only for as long as the dialog is open: it is shown once and
  // not kept anywhere after that.
  const [issued, setIssued] = useState<{ user: ManagedUser; password: string } | null>(null);
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

  const handleReset = async (target: ManagedUser) => {
    setError(null);
    try {
      const result = await resetPassword.mutateAsync(target.id);
      setConfirmingReset(null);
      setIssued({ user: target, password: result.temporary_password });
    } catch (err) {
      setError(readError(err, "Failed to reset the password"));
    }
  };

  return (
    <div>
      {/* While the dialog is open it shows the error itself -- rendering it
          here too would duplicate it, and behind the modal backdrop. */}
      {error && !confirmingDeactivation && !confirmingReset && <p role="alert">{error}</p>}
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
                    <>
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
                      {user.is_active && (
                        <button
                          aria-label={`Reset password for ${user.name}`}
                          onClick={() => setConfirmingReset(user)}
                          disabled={resetPassword.isPending}
                        >
                          Reset password
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {confirmingReset && (
        <ConfirmDialog
          title={`Reset the password for ${confirmingReset.name}?`}
          message="They are signed out everywhere and their current password stops working. You'll be shown a one-time password to give them; they must choose their own when they next sign in."
          confirmLabel="Reset password"
          pendingLabel="Resetting..."
          isPending={resetPassword.isPending}
          error={error}
          onConfirm={() => handleReset(confirmingReset)}
          onCancel={() => setConfirmingReset(null)}
        />
      )}

      {issued && (
        <div className="modal-backdrop">
          <div
            className="modal-panel confirm-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-label="Temporary password"
          >
            <div className="modal-header">
              <div>
                <h3>Temporary password for {issued.user.name}</h3>
                <p>
                  Copy it now and pass it on privately. It won't be shown again, and they must
                  replace it when they sign in.
                </p>
              </div>
            </div>
            <p>
              <code className="temporary-password" data-testid="temporary-password">
                {issued.password}
              </code>
            </p>
            <div className="confirm-dialog-actions">
              <button onClick={() => navigator.clipboard?.writeText(issued.password)}>Copy</button>
              <button onClick={() => setIssued(null)}>Done</button>
            </div>
          </div>
        </div>
      )}

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

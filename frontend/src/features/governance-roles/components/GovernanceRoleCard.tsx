import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory, useUsers } from "../../users/hooks";
import {
  useAssignGovernanceRole,
  useCaigoDelegation,
  useDeleteGovernanceRole,
  useRevokeCaigoDelegation,
  useSetCaigoDelegation,
  useUnassignGovernanceRole,
  useUpdateGovernanceRole,
} from "../hooks";
import type { GovernanceRole } from "../types";

const CHIEF_AI_GOVERNANCE_OFFICER = "Chief AI Governance Officer";

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

interface GovernanceRoleCardProps {
  role: GovernanceRole;
  allRoles: GovernanceRole[];
  canManage: boolean;
}

function CaigoDelegationSection({ canManage }: { canManage: boolean }) {
  const { data: delegation, isLoading } = useCaigoDelegation();
  const { data: admins } = useUsers({ enabled: canManage });
  const setDelegation = useSetCaigoDelegation();
  const revokeDelegation = useRevokeCaigoDelegation();

  const [delegateUserId, setDelegateUserId] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>, fallback: string) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(readError(err, fallback));
    }
  };

  if (isLoading) return null;

  const eligibleAdmins = (admins ?? []).filter((u) => u.role === "admin" && u.is_active);

  return (
    <div className="governance-role-field">
      <h4>Backup approver</h4>
      {error && <p role="alert">{error}</p>}
      {delegation ? (
        <p>
          {delegation.delegate_name} covers this role until{" "}
          {new Date(delegation.ends_at).toLocaleString()}.
          {canManage && (
            <button
              onClick={() =>
                run(() => revokeDelegation.mutateAsync(), "Failed to revoke this delegation")
              }
              disabled={revokeDelegation.isPending}
            >
              Revoke
            </button>
          )}
        </p>
      ) : (
        <p className="framework-tags-empty">No backup approver is currently active.</p>
      )}

      {canManage && (
        <div className="governance-role-field-row">
          <select
            aria-label="Backup approver"
            value={delegateUserId}
            onChange={(e) => setDelegateUserId(e.target.value)}
          >
            <option value="">Select an admin</option>
            {eligibleAdmins.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
          <input
            aria-label="Backup approver expires at"
            type="datetime-local"
            value={endsAt}
            onChange={(e) => setEndsAt(e.target.value)}
          />
          <button
            disabled={!delegateUserId || !endsAt || setDelegation.isPending}
            onClick={() =>
              run(async () => {
                await setDelegation.mutateAsync({
                  delegate_user_id: Number(delegateUserId),
                  ends_at: new Date(endsAt).toISOString(),
                });
                setDelegateUserId("");
                setEndsAt("");
              }, "Failed to set this backup approver")
            }
          >
            Set Backup Approver
          </button>
        </div>
      )}
    </div>
  );
}

export function GovernanceRoleCard({ role, allRoles, canManage }: GovernanceRoleCardProps) {
  const { data: directory } = useUserDirectory();
  const update = useUpdateGovernanceRole();
  const deleteRole = useDeleteGovernanceRole();
  const assign = useAssignGovernanceRole();
  const unassign = useUnassignGovernanceRole();

  const [responsibilities, setResponsibilities] = useState(role.responsibilities);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const holderIds = new Set(role.holders.map((h) => h.id));
  const assignableUsers = (directory ?? []).filter((u) => !holderIds.has(u.id));
  const atCapacity = role.max_holders !== null && role.holders.length >= role.max_holders;
  const parentOptions = allRoles.filter((r) => r.id !== role.id);

  const run = async (action: () => Promise<unknown>, fallback: string) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(readError(err, fallback));
    }
  };

  return (
    <div className="governance-role-card">
      <div className="governance-role-card-header">
        <h3>{role.name}</h3>
        <span className="impact-review-chip">
          {role.max_holders !== null
            ? `${role.holders.length} of ${role.max_holders}`
            : `${role.holders.length} holder${role.holders.length === 1 ? "" : "s"}`}
        </span>
      </div>

      {error && <p role="alert">{error}</p>}

      {canManage ? (
        <textarea
          aria-label={`Responsibilities for ${role.name}`}
          rows={2}
          value={responsibilities}
          onChange={(e) => setResponsibilities(e.target.value)}
          onBlur={() =>
            responsibilities !== role.responsibilities &&
            run(
              () => update.mutateAsync({ roleId: role.id, data: { responsibilities } }),
              "Failed to save responsibilities",
            )
          }
        />
      ) : (
        <p>{role.responsibilities}</p>
      )}

      {canManage && (
        <div className="governance-role-field">
          <label htmlFor={`reports-to-${role.id}`}>Reports to</label>
          <select
            id={`reports-to-${role.id}`}
            value={role.parent_role_id ?? ""}
            onChange={(e) =>
              run(
                () =>
                  update.mutateAsync({
                    roleId: role.id,
                    data: { parent_role_id: e.target.value ? Number(e.target.value) : null },
                  }),
                "Failed to change who this role reports to",
              )
            }
          >
            <option value="">Nobody (top of the chart)</option>
            {parentOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <h4>Holders</h4>
      {role.holders.length === 0 ? (
        <p className="framework-tags-empty">No one holds this role yet.</p>
      ) : (
        <ul className="governance-role-holders">
          {role.holders.map((holder) => (
            <li key={holder.id}>
              {holder.name}
              {canManage && (
                <button
                  onClick={() =>
                    run(
                      () => unassign.mutateAsync({ roleId: role.id, userId: holder.id }),
                      "Failed to remove this holder",
                    )
                  }
                >
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {role.name === CHIEF_AI_GOVERNANCE_OFFICER && <CaigoDelegationSection canManage={canManage} />}

      {canManage && !atCapacity && (
        <div className="governance-role-field-row">
          <select
            aria-label={`Assign a user to ${role.name}`}
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
          >
            <option value="">Select a user</option>
            {assignableUsers.map((user) => (
              <option key={user.id} value={user.id}>
                {formatUserOption(user)}
              </option>
            ))}
          </select>
          <button
            disabled={!selectedUserId || assign.isPending}
            onClick={() =>
              run(async () => {
                await assign.mutateAsync({ roleId: role.id, userId: Number(selectedUserId) });
                setSelectedUserId("");
              }, "Failed to assign this user")
            }
          >
            Assign
          </button>
        </div>
      )}

      {canManage && (
        <button
          onClick={() => run(() => deleteRole.mutateAsync(role.id), "Failed to delete this role")}
          disabled={deleteRole.isPending}
        >
          Delete Role
        </button>
      )}
    </div>
  );
}

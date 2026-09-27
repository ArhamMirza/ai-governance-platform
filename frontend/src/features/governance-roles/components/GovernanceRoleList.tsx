import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useCreateGovernanceRole, useGovernanceRoles } from "../hooks";
import { GovernanceRoleCard } from "./GovernanceRoleCard";

interface GovernanceRoleListProps {
  canManage: boolean;
}

export function GovernanceRoleList({ canManage }: GovernanceRoleListProps) {
  const { data: roles, isLoading, isError } = useGovernanceRoles();
  const createRole = useCreateGovernanceRole();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [responsibilities, setResponsibilities] = useState("");
  const [parentRoleId, setParentRoleId] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading roles...</p>;
  if (isError || !roles) return <p>Failed to load governance roles.</p>;

  const handleCreate = async () => {
    setError(null);
    try {
      await createRole.mutateAsync({
        name,
        responsibilities,
        parent_role_id: parentRoleId ? Number(parentRoleId) : null,
      });
      setName("");
      setResponsibilities("");
      setParentRoleId("");
      setShowForm(false);
    } catch (err) {
      setError(readError(err, "Failed to create this role"));
    }
  };

  return (
    <>
      {canManage && (
        <div className="section-toolbar">
          <button
            className={showForm ? undefined : "is-primary"}
            onClick={() => setShowForm((prev) => !prev)}
          >
            {showForm ? "Cancel" : "Add Role"}
          </button>
        </div>
      )}

      {showForm && (
        <div className="governance-role-card is-new-role">
          {error && <p role="alert">{error}</p>}
          <div className="governance-role-field">
            <label htmlFor="new-role-name">Role name</label>
            <input id="new-role-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="governance-role-field">
            <label htmlFor="new-role-responsibilities">Responsibilities</label>
            <textarea
              id="new-role-responsibilities"
              rows={2}
              value={responsibilities}
              onChange={(e) => setResponsibilities(e.target.value)}
            />
          </div>
          <div className="governance-role-field">
            <label htmlFor="new-role-parent">Reports to</label>
            <select
              id="new-role-parent"
              aria-label="Reports to for the new role"
              value={parentRoleId}
              onChange={(e) => setParentRoleId(e.target.value)}
            >
              <option value="">Nobody (top of the chart)</option>
              {roles.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                </option>
              ))}
            </select>
          </div>
          <footer className="governance-role-actions">
            <button
              className="is-primary"
              onClick={handleCreate}
              disabled={!name.trim() || !responsibilities.trim() || createRole.isPending}
            >
              {createRole.isPending ? "Creating..." : "Create Role"}
            </button>
          </footer>
        </div>
      )}

      <div className="governance-role-grid">
        {roles.map((role) => (
          <GovernanceRoleCard key={role.id} role={role} allRoles={roles} canManage={canManage} />
        ))}
      </div>
    </>
  );
}

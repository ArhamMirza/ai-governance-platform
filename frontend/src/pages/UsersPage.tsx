import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { SecuritySettingsPanel } from "../features/users/components/SecuritySettingsPanel";
import { ImportUsersPanel } from "../features/users/components/ImportUsersPanel";
import { UserForm } from "../features/users/components/UserForm";
import { UsersList } from "../features/users/components/UsersList";

export function UsersPage() {
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const { data: me } = useCurrentUser();

  if (me && !hasPermission(me.role, "manage_users")) {
    return (
      <section>
        <h1>Users</h1>
        <p>Only admins can manage user accounts.</p>
      </section>
    );
  }

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Users</h1>
          <p>Manage who can access this workspace, and their role.</p>
        </div>
        <div className="page-header-actions">
          <button onClick={() => setShowImport((prev) => !prev)}>
            {showImport ? "Close import" : "Import from CSV"}
          </button>
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New User"}
          </button>
        </div>
      </div>
      {showForm && <UserForm onCreated={() => setShowForm(false)} />}
      {showImport && <ImportUsersPanel onClose={() => setShowImport(false)} />}

      <SecuritySettingsPanel />

      <UsersList />
    </section>
  );
}

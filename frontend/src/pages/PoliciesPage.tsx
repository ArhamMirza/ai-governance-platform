import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { PolicyForm } from "../features/policies/components/PolicyForm";
import { PolicyList } from "../features/policies/components/PolicyList";

export function PoliciesPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Policies</h1>
          <p>Organization-wide policies are managed here.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Policy"}
          </button>
        )}
      </div>
      {showForm && <PolicyForm onCreated={() => setShowForm(false)} />}

      <PolicyList />
    </section>
  );
}

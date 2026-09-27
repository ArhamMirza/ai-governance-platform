import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { CorrectiveActionForm } from "../features/corrective-actions/components/CorrectiveActionForm";
import { CorrectiveActionList } from "../features/corrective-actions/components/CorrectiveActionList";

export function CorrectiveActionsPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Corrective Actions</h1>
          <p>Nonconformities, tracked from root cause through a verified close.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Corrective Action"}
          </button>
        )}
      </div>
      {showForm && <CorrectiveActionForm onCreated={() => setShowForm(false)} />}

      <CorrectiveActionList />
    </section>
  );
}

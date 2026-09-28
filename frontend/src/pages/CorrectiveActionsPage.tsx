import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { CorrectiveActionForm } from "../features/corrective-actions/components/CorrectiveActionForm";
import { CorrectiveActionList } from "../features/corrective-actions/components/CorrectiveActionList";

/** Carried in navigate(path, { state }) when raised from an audit finding or
 * an AI incident (see the "Raise Corrective Action" buttons on AuditDetail
 * and IncidentDetail) -- the assignee and due date stay a deliberate choice
 * made here, not passed through. */
interface RaiseFromSourceState {
  sourceType: string;
  sourceId: number;
  nonconformityDescription: string;
}

export function CorrectiveActionsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const fromSource = location.state as RaiseFromSourceState | null;
  const [showForm, setShowForm] = useState(Boolean(fromSource));
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
      {showForm && (
        <CorrectiveActionForm
          initialNonconformityDescription={fromSource?.nonconformityDescription}
          sourceType={fromSource?.sourceType}
          sourceId={fromSource?.sourceId}
          onCreated={(id) => {
            setShowForm(false);
            // Clears the router state so a reload/back doesn't re-open the
            // form pre-filled with a source that's now already raised.
            navigate(`/corrective-actions/${id}`, { replace: true });
          }}
        />
      )}

      <CorrectiveActionList />
    </section>
  );
}

import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { CorrectiveActionForm } from "../features/corrective-actions/components/CorrectiveActionForm";
import { CorrectiveActionList } from "../features/corrective-actions/components/CorrectiveActionList";

/** Carried in navigate(path, { state }) when raised from an audit finding
 * (see AuditDetail's "Raise Corrective Action" button) -- the assignee and
 * due date stay a deliberate choice made here, not passed through. */
interface RaiseFromFindingState {
  sourceType: string;
  sourceId: number;
  nonconformityDescription: string;
}

export function CorrectiveActionsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const fromFinding = location.state as RaiseFromFindingState | null;
  const [showForm, setShowForm] = useState(Boolean(fromFinding));
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
          initialNonconformityDescription={fromFinding?.nonconformityDescription}
          sourceType={fromFinding?.sourceType}
          sourceId={fromFinding?.sourceId}
          onCreated={(id) => {
            setShowForm(false);
            // Clears the router state so a reload/back doesn't re-open the
            // form pre-filled with a finding that's now already raised.
            navigate(`/corrective-actions/${id}`, { replace: true });
          }}
        />
      )}

      <CorrectiveActionList />
    </section>
  );
}

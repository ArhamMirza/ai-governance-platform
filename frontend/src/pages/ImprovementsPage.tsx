import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import {
  ImprovementForm,
  type ImprovementSourceRecord,
} from "../features/improvements/components/ImprovementForm";
import { ImprovementList } from "../features/improvements/components/ImprovementList";

export function ImprovementsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  // Carried in navigate(path, { state }) by SourceImprovements' "Raise
  // Improvement" button.
  const from = (location.state as ImprovementSourceRecord | null) ?? undefined;
  const [showForm, setShowForm] = useState(Boolean(from));
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Improvements</h1>
          <p>
            Opportunities to improve the AI management system, and what came of them (ISO 42001
            10.1). Nonconformities go to Corrective Actions.
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Improvement"}
          </button>
        )}
      </div>
      {showForm && (
        <ImprovementForm
          from={from}
          onCreated={(id) =>
            // Clears the router state so a reload/back doesn't re-open the
            // form pre-filled from a source that's now already raised.
            navigate(`/improvements/${id}`, { replace: true })
          }
        />
      )}

      <ImprovementList />
    </section>
  );
}

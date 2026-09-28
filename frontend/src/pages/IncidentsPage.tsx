import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { IncidentForm } from "../features/incidents/components/IncidentForm";
import { IncidentList } from "../features/incidents/components/IncidentList";

export function IncidentsPage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>AI Incidents</h1>
          <p>What went wrong in operation, and whether serious incidents were reported in time.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Log Incident"}
          </button>
        )}
      </div>
      {showForm && <IncidentForm onCreated={(id) => navigate(`/incidents/${id}`)} />}

      <IncidentList />
    </section>
  );
}

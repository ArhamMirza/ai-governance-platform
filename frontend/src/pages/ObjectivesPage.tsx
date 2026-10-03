import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { ObjectiveForm } from "../features/objectives/components/ObjectiveForm";
import { ObjectiveList } from "../features/objectives/components/ObjectiveList";

export function ObjectivesPage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>AI Objectives</h1>
          <p>What the AI management system is aiming for, and how it's measured (ISO 42001 6.2, 9.1).</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Objective"}
          </button>
        )}
      </div>
      {showForm && <ObjectiveForm onCreated={(id) => navigate(`/objectives/${id}`)} />}

      <ObjectiveList />
    </section>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { ChangeForm } from "../features/changes/components/ChangeForm";
import { ChangeList } from "../features/changes/components/ChangeList";

export function ChangesPage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Changes</h1>
          <p>
            Planned changes to the AI management system, and how they're carried out (ISO 42001
            6.3).
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Change"}
          </button>
        )}
      </div>
      {showForm && <ChangeForm onCreated={(id) => navigate(`/changes/${id}`)} />}

      <ChangeList />
    </section>
  );
}

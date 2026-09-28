import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { CompetenceRequirementForm } from "../features/competence/components/CompetenceRequirementForm";
import { CompetenceRequirementList } from "../features/competence/components/CompetenceRequirementList";

export function CompetencePage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Competence</h1>
          <p>The training and awareness each role needs, and who has it.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Requirement"}
          </button>
        )}
      </div>
      {showForm && (
        <CompetenceRequirementForm onCreated={(id) => navigate(`/competence/${id}`)} />
      )}

      <CompetenceRequirementList />
    </section>
  );
}

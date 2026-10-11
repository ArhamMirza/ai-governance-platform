import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { CommunicationForm } from "../features/communications/components/CommunicationForm";
import { CommunicationList } from "../features/communications/components/CommunicationList";

export function CommunicationsPage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Communication</h1>
          <p>
            What the organization communicates about the AI management system, to whom, how and
            how often, internally and externally (ISO 42001 7.4).
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Communication"}
          </button>
        )}
      </div>
      {showForm && <CommunicationForm onCreated={(id) => navigate(`/communications/${id}`)} />}

      <CommunicationList />
    </section>
  );
}

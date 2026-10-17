import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AIToolForm } from "../features/ai-tools/components/AIToolForm";
import { AIToolList } from "../features/ai-tools/components/AIToolList";
import { RequestQueue } from "../features/ai-tools/components/RequestQueue";
import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";

export function AIToolsPage() {
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>AI Tools</h1>
          <p>
            Third-party AI tools staff might use, and which are approved. Employees ask for a tool;
            the Chief AI Governance Officer decides (ISO 42001 A.9.2).
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Tool"}
          </button>
        )}
      </div>
      {showForm && <AIToolForm onCreated={(id) => navigate(`/ai-tools/${id}`)} />}

      <h2>Requests</h2>
      <RequestQueue />

      <h2>Register</h2>
      <AIToolList />
    </section>
  );
}

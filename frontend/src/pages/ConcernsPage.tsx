import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConcernList } from "../features/concerns/components/ConcernList";
import { ConcernSettingsPanel } from "../features/concerns/components/ConcernSettingsPanel";
import { LogConcernForm } from "../features/concerns/components/LogConcernForm";
import { useConcernAccess } from "../features/concerns/hooks";

export function ConcernsPage() {
  const { data: access, isLoading } = useConcernAccess();
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();

  if (isLoading) return <p>Loading...</p>;
  if (!access?.can_handle) {
    return (
      <section>
        <h1>Concerns</h1>
        <p>Only administrators can read and handle concerns raised by staff.</p>
      </section>
    );
  }

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Concerns</h1>
          <p>
            What staff have raised about the organization's AI systems, named or anonymous (ISO 42001
            A.3.3). Only you can read these.
          </p>
        </div>
        <button onClick={() => setShowForm((prev) => !prev)}>
          {showForm ? "Cancel" : "Record a Concern"}
        </button>
      </div>
      {showForm && <LogConcernForm onLogged={(id) => navigate(`/concerns/${id}`)} />}

      <ConcernList />
      <ConcernSettingsPanel />
    </section>
  );
}

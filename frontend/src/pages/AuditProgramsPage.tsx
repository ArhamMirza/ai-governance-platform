import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { AuditProgramForm } from "../features/internal-audits/components/AuditProgramForm";
import { AuditProgramList } from "../features/internal-audits/components/AuditProgramList";

export function AuditProgramsPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Internal Audits</h1>
          <p>Audit programs, on an interval or ad hoc, and what they find.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Audit Program"}
          </button>
        )}
      </div>
      {showForm && <AuditProgramForm onCreated={() => setShowForm(false)} />}

      <AuditProgramList />
    </section>
  );
}

import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { ProcedureForm } from "../features/procedures/components/ProcedureForm";
import { ProcedureList } from "../features/procedures/components/ProcedureList";

export function ProceduresPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Procedures</h1>
          <p>Organization-wide procedures are managed here.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Procedure"}
          </button>
        )}
      </div>
      {showForm && <ProcedureForm onCreated={() => setShowForm(false)} />}

      <ProcedureList />
    </section>
  );
}

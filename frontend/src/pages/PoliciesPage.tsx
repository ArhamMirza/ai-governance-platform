import { useState } from "react";

import { PolicyForm } from "../features/policies/components/PolicyForm";
import { PolicyList } from "../features/policies/components/PolicyList";

export function PoliciesPage() {
  const [showForm, setShowForm] = useState(false);

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Policies</h1>
          <p>Organization-wide policies are managed here.</p>
        </div>
        <button onClick={() => setShowForm((prev) => !prev)}>
          {showForm ? "Cancel" : "New Policy"}
        </button>
      </div>
      {showForm && <PolicyForm onCreated={() => setShowForm(false)} />}

      <PolicyList />
    </section>
  );
}

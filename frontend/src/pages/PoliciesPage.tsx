import { useState } from "react";

import { PolicyForm } from "../features/policies/components/PolicyForm";
import { PolicyList } from "../features/policies/components/PolicyList";

export function PoliciesPage() {
  const [showForm, setShowForm] = useState(false);

  return (
    <section>
      <h1>Policies</h1>
      <p>Organization-wide policies are managed here.</p>

      <button onClick={() => setShowForm((prev) => !prev)}>
        {showForm ? "Cancel" : "New Policy"}
      </button>
      {showForm && <PolicyForm onCreated={() => setShowForm(false)} />}

      <PolicyList />
    </section>
  );
}

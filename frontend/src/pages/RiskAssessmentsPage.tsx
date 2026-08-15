import { useState } from "react";

import { RiskAssessmentForm } from "../features/risk-assessments/components/RiskAssessmentForm";
import { RiskAssessmentList } from "../features/risk-assessments/components/RiskAssessmentList";

export function RiskAssessmentsPage() {
  const [showForm, setShowForm] = useState(false);

  return (
    <section>
      <h1>Risk Assessments</h1>
      <p>Risk assessments for a selected AI System appear here.</p>

      <button onClick={() => setShowForm((prev) => !prev)}>
        {showForm ? "Cancel" : "New Risk Assessment"}
      </button>
      {showForm && <RiskAssessmentForm onCreated={() => setShowForm(false)} />}

      <RiskAssessmentList />
    </section>
  );
}

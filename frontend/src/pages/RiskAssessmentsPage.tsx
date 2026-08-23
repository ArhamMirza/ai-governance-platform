import { useState } from "react";

import { RiskAssessmentForm } from "../features/risk-assessments/components/RiskAssessmentForm";
import { RiskAssessmentList } from "../features/risk-assessments/components/RiskAssessmentList";
import { RiskPortfolioSummaryView } from "../features/risk-assessments/components/RiskPortfolioSummaryView";
import { RiskCriteriaEditor } from "../features/risk-criteria/components/RiskCriteriaEditor";

export function RiskAssessmentsPage() {
  const [showForm, setShowForm] = useState(false);

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Risk Assessments</h1>
          <p>Risk assessments for a selected AI System appear here.</p>
        </div>
        <button onClick={() => setShowForm((prev) => !prev)}>
          {showForm ? "Cancel" : "New Risk Assessment"}
        </button>
      </div>
      {showForm && <RiskAssessmentForm onCreated={() => setShowForm(false)} />}

      <RiskPortfolioSummaryView />

      <RiskCriteriaEditor />

      <h3>All Assessments</h3>
      <RiskAssessmentList />
    </section>
  );
}

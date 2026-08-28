import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { AssessmentCoverageTable } from "../features/impact-assessments/components/AssessmentCoverageTable";
import { RiskAssessmentForm } from "../features/risk-assessments/components/RiskAssessmentForm";
import { RiskAssessmentList } from "../features/risk-assessments/components/RiskAssessmentList";
import { RiskPortfolioSummaryView } from "../features/risk-assessments/components/RiskPortfolioSummaryView";
import { RiskCriteriaEditor } from "../features/risk-criteria/components/RiskCriteriaEditor";

export function RiskAssessmentsPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");
  const canManageSettings = hasPermission(me?.role, "manage_settings");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Impact &amp; Risk Assessments</h1>
          <p>
            Every AI system is impact-assessed first (ISO 42001 clause 8.4), which unlocks its
            risk assessment. Both are reviewed yearly.
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Risk Assessment"}
          </button>
        )}
      </div>
      {showForm && <RiskAssessmentForm onCreated={() => setShowForm(false)} />}

      <h3>Assessment Coverage</h3>
      <AssessmentCoverageTable />

      <RiskPortfolioSummaryView />

      {canManageSettings && <RiskCriteriaEditor />}

      <h3>All Risk Assessments</h3>
      <RiskAssessmentList />
    </section>
  );
}

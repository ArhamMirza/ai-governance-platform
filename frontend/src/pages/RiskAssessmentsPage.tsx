import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
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
          <h1>Risk Assessments</h1>
          <p>Risk assessments for a selected AI System appear here.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "New Risk Assessment"}
          </button>
        )}
      </div>
      {showForm && <RiskAssessmentForm onCreated={() => setShowForm(false)} />}

      <RiskPortfolioSummaryView />

      {canManageSettings && <RiskCriteriaEditor />}

      <h3>All Assessments</h3>
      <RiskAssessmentList />
    </section>
  );
}

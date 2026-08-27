import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { riskAssessmentKey, useUpdateRiskAssessment } from "../hooks";
import type { RiskAssessment, RiskAssessmentStatus } from "../types";

interface RiskAssessmentHeaderProps {
  riskAssessment: RiskAssessment;
  aiSystemName: string;
}

export function RiskAssessmentHeader({ riskAssessment, aiSystemName }: RiskAssessmentHeaderProps) {
  const updateRiskAssessment = useUpdateRiskAssessment(riskAssessment.id);

  return (
    <div className="risk-header">
      <p>AI System: {aiSystemName}</p>
      <div className="risk-header-row">
        <label htmlFor="risk-assessment-status">Status</label>
        <select
          id="risk-assessment-status"
          value={riskAssessment.status}
          onChange={(e) =>
            updateRiskAssessment.mutate({ status: e.target.value as RiskAssessmentStatus })
          }
        >
          <option value="draft">Draft</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
      </div>
      <div className="risk-header-tags">
        <span className="risk-header-tags-label">Framework Tags</span>
        <FrameworkTagPicker
          entityType="RiskAssessment"
          entityId={riskAssessment.id}
          extraInvalidateKeys={[riskAssessmentKey(riskAssessment.id)]}
        />
      </div>
      <p className="risk-rating">
        Overall Risk Rating:{" "}
        {riskAssessment.overall_risk_rating !== null
          ? riskAssessment.overall_risk_rating
          : "Not yet scored"}
      </p>
    </div>
  );
}

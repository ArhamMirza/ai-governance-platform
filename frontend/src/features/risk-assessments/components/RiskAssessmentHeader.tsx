import { useUpdateRiskAssessment } from "../hooks";
import type { RiskAssessment, RiskAssessmentStatus } from "../types";

interface RiskAssessmentHeaderProps {
  riskAssessment: RiskAssessment;
  aiSystemName: string;
}

export function RiskAssessmentHeader({ riskAssessment, aiSystemName }: RiskAssessmentHeaderProps) {
  const updateRiskAssessment = useUpdateRiskAssessment(riskAssessment.id);

  return (
    <div>
      <p>AI System: {aiSystemName}</p>
      <p>
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
      </p>
      <p>Framework Tags: {riskAssessment.framework_tags.join(", ") || "None"}</p>
      <p>
        Overall Risk Rating:{" "}
        {riskAssessment.overall_risk_rating !== null
          ? riskAssessment.overall_risk_rating
          : "Not yet scored"}
      </p>
    </div>
  );
}

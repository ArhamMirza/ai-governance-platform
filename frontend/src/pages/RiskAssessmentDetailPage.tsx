import { useParams } from "react-router-dom";

import { RiskAssessmentDetail } from "../features/risk-assessments/components/RiskAssessmentDetail";

export function RiskAssessmentDetailPage() {
  const { riskAssessmentId } = useParams<{ riskAssessmentId: string }>();
  const id = Number(riskAssessmentId);

  if (!riskAssessmentId || Number.isNaN(id)) return <p>Invalid risk assessment id.</p>;

  return <RiskAssessmentDetail riskAssessmentId={id} />;
}

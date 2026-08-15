import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows, useRiskAssessments } from "../hooks";

export function RiskAssessmentList() {
  const { data: riskAssessments, isLoading, isError } = useRiskAssessments();
  const { data: inventory } = useAISystemInventoryRows();

  if (isLoading) return <p>Loading risk assessments...</p>;
  if (isError) return <p>Failed to load risk assessments.</p>;
  if (!riskAssessments || riskAssessments.length === 0) return <p>No risk assessments yet.</p>;

  const nameForRow = (rowId: number) => {
    const row = inventory?.rows.find((r) => r.id === rowId);
    const name = row?.data.name;
    return typeof name === "string" && name ? name : `AI System #${rowId}`;
  };

  return (
    <table>
      <thead>
        <tr>
          <th>AI System</th>
          <th>Status</th>
          <th>Overall Risk Rating</th>
        </tr>
      </thead>
      <tbody>
        {riskAssessments.map((riskAssessment) => (
          <tr key={riskAssessment.id}>
            <td>
              <Link to={`/risk-assessments/${riskAssessment.id}`}>
                {nameForRow(riskAssessment.ai_system_row_id)}
              </Link>
            </td>
            <td>
              <StatusBadge status={riskAssessment.status} />
            </td>
            <td>{riskAssessment.overall_risk_rating ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

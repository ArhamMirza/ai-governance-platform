import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows, useRiskPortfolioSummary } from "../hooks";
import { severityForScore } from "../riskSeverity";

export function RiskAssessmentList() {
  const { data: summary, isLoading, isError } = useRiskPortfolioSummary();
  const { data: inventory } = useAISystemInventoryRows();

  if (isLoading) return <p>Loading risk assessments...</p>;
  if (isError || !summary) return <p>Failed to load risk assessments.</p>;
  if (summary.assessments.length === 0) return <p>No risk assessments yet.</p>;

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
          <th>Risk Items</th>
          <th>Overdue</th>
        </tr>
      </thead>
      <tbody>
        {summary.assessments.map((assessment) => (
          <tr key={assessment.id} className={assessment.overdue_count > 0 ? "row-flagged" : undefined}>
            <td>
              <Link to={`/risk-assessments/${assessment.id}`}>
                {nameForRow(assessment.ai_system_row_id)}
              </Link>
            </td>
            <td>
              <StatusBadge status={assessment.status} />
            </td>
            <td>
              {assessment.overall_risk_rating !== null ? (
                <span
                  className="score-pill"
                  data-severity={severityForScore(
                    assessment.overall_risk_rating,
                    summary.criteria,
                  )}
                >
                  {assessment.overall_risk_rating}
                </span>
              ) : (
                "—"
              )}
            </td>
            <td>
              <span className="item-breakdown">
                <span>{assessment.item_count}</span>
                {assessment.high_count > 0 && (
                  <span className="item-high">{assessment.high_count} high</span>
                )}
              </span>
            </td>
            <td>
              {assessment.overdue_count > 0 ? (
                <span className="flag-chip">{assessment.overdue_count}</span>
              ) : (
                "—"
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

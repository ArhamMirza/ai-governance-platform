import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/httpClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useCreateRiskAssessment, useRiskAssessments } from "../../risk-assessments/hooks";
import { useAllImpactAssessments, useCreateImpactAssessmentForAISystem } from "../hooks";
import type { ImpactAssessment } from "../types";

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

function impactStatusCell(assessment: ImpactAssessment | undefined) {
  if (!assessment) return <span className="impact-review-chip">Not started</span>;
  if (assessment.status !== "completed") {
    return <span className="impact-review-chip">Draft</span>;
  }
  return (
    <span className={`impact-review-chip${assessment.review_overdue ? " is-overdue" : ""}`}>
      {assessment.review_overdue ? "Review overdue" : "Completed"}
      {assessment.next_review_date ? ` · due ${assessment.next_review_date}` : ""}
    </span>
  );
}

/** One impact assessment and one risk assessment per AI system, in that
 * order. This table is the entry point for both. */
export function AssessmentCoverageTable() {
  const { data: inventory, isLoading } = useAISystemInventoryRows();
  const { data: impactAssessments } = useAllImpactAssessments();
  const { data: riskAssessments } = useRiskAssessments();
  const createImpactAssessment = useCreateImpactAssessmentForAISystem();
  const createRiskAssessment = useCreateRiskAssessment();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading AI systems...</p>;

  const rows = inventory?.rows ?? [];
  if (rows.length === 0) {
    return <p>No AI systems in the inventory yet. Add one before assessing it.</p>;
  }

  const startImpactAssessment = async (aiSystemRowId: number) => {
    setError(null);
    try {
      const created = await createImpactAssessment.mutateAsync(aiSystemRowId);
      navigate(`/impact-assessments/${created.id}`);
    } catch (err) {
      setError(readError(err, "Failed to start impact assessment"));
    }
  };

  const startRiskAssessment = async (aiSystemRowId: number) => {
    setError(null);
    try {
      const created = await createRiskAssessment.mutateAsync({
        ai_system_row_id: aiSystemRowId,
      });
      navigate(`/risk-assessments/${created.id}`);
    } catch (err) {
      setError(readError(err, "Failed to start risk assessment"));
    }
  };

  const pending = createImpactAssessment.isPending || createRiskAssessment.isPending;

  return (
    <>
      {error && <p role="alert">{error}</p>}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>AI System</th>
              <th>Impact Assessment</th>
              <th>Risk Assessment</th>
              <th>Next Step</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const impact = (impactAssessments ?? []).find(
                (a) => a.ai_system_row_id === row.id,
              );
              const risk = (riskAssessments ?? []).find((r) => r.ai_system_row_id === row.id);
              const name =
                typeof row.data.name === "string" && row.data.name
                  ? row.data.name
                  : `AI System #${row.id}`;

              return (
                <tr key={row.id}>
                  <td>{name}</td>
                  <td>
                    {impact ? (
                      <Link to={`/impact-assessments/${impact.id}`}>
                        {impactStatusCell(impact)}
                      </Link>
                    ) : (
                      impactStatusCell(undefined)
                    )}
                  </td>
                  <td>
                    {risk ? (
                      <Link to={`/risk-assessments/${risk.id}`}>Open</Link>
                    ) : impact?.status === "completed" ? (
                      <span className="impact-review-chip">Not started</span>
                    ) : (
                      <span className="impact-review-chip">Blocked &mdash; impact first</span>
                    )}
                  </td>
                  <td>
                    {!impact ? (
                      <button onClick={() => startImpactAssessment(row.id)} disabled={pending}>
                        Start Impact Assessment
                      </button>
                    ) : impact.status !== "completed" ? (
                      <button onClick={() => navigate(`/impact-assessments/${impact.id}`)}>
                        Complete Impact Assessment
                      </button>
                    ) : !risk ? (
                      <button onClick={() => startRiskAssessment(row.id)} disabled={pending}>
                        Start Risk Assessment
                      </button>
                    ) : (
                      <span className="framework-tags-empty">
                        Both assessments in place. Add risks as rows.
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/httpClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useRiskAssessments } from "../../risk-assessments/hooks";
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

/** Highest id == most recently created, which is the one to open. */
function latestFor(assessments: ImpactAssessment[]): ImpactAssessment {
  return assessments.reduce((a, b) => (b.id > a.id ? b : a));
}

function impactStatusCell(assessments: ImpactAssessment[]) {
  if (assessments.length === 0) return <span className="impact-review-chip">Not started</span>;

  const completed = assessments.filter((a) => a.status === "completed");
  if (completed.length === 0) return <span className="impact-review-chip">Draft</span>;

  // The most recent completed one governs the review date.
  const latest = completed.reduce((a, b) => (b.id > a.id ? b : a));
  return (
    <span className={`impact-review-chip${latest.review_overdue ? " is-overdue" : ""}`}>
      {latest.review_overdue ? "Review overdue" : "Completed"}
      {latest.next_review_date ? ` · due ${latest.next_review_date}` : ""}
    </span>
  );
}

/** The impact-first view: every AI system, whether its impact assessment is
 * done, and whether risk assessment has been unlocked as a result. */
export function AssessmentCoverageTable() {
  const { data: inventory, isLoading } = useAISystemInventoryRows();
  const { data: impactAssessments } = useAllImpactAssessments();
  const { data: riskAssessments } = useRiskAssessments();
  const createImpactAssessment = useCreateImpactAssessmentForAISystem();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading AI systems...</p>;

  const rows = inventory?.rows ?? [];
  if (rows.length === 0) {
    return <p>No AI systems in the inventory yet. Add one before assessing it.</p>;
  }

  const handleStart = async (aiSystemRowId: number) => {
    setError(null);
    try {
      const created = await createImpactAssessment.mutateAsync(aiSystemRowId);
      navigate(`/impact-assessments/${created.id}`);
    } catch (err) {
      setError(readError(err, "Failed to start impact assessment"));
    }
  };

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
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const forSystem = (impactAssessments ?? []).filter(
                (a) => a.ai_system_row_id === row.id,
              );
              const risk = (riskAssessments ?? []).find((r) => r.ai_system_row_id === row.id);
              const hasCompletedImpact = forSystem.some((a) => a.status === "completed");
              const name =
                typeof row.data.name === "string" && row.data.name
                  ? row.data.name
                  : `AI System #${row.id}`;

              return (
                <tr key={row.id}>
                  <td>{name}</td>
                  <td>{impactStatusCell(forSystem)}</td>
                  <td>
                    {risk ? (
                      <Link to={`/risk-assessments/${risk.id}`}>View</Link>
                    ) : hasCompletedImpact ? (
                      <span className="impact-review-chip">Ready to start</span>
                    ) : (
                      <span className="impact-review-chip">Blocked &mdash; impact first</span>
                    )}
                  </td>
                  <td>
                    {forSystem.length === 0 ? (
                      <button
                        onClick={() => handleStart(row.id)}
                        disabled={createImpactAssessment.isPending}
                      >
                        Start Impact Assessment
                      </button>
                    ) : (
                      <Link to={`/impact-assessments/${latestFor(forSystem).id}`}>
                        Open Impact Assessment
                      </Link>
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

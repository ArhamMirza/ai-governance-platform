import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { useCreateImpactAssessment, useImpactAssessments } from "../hooks";
import { ImpactAssessmentForm } from "./ImpactAssessmentForm";

interface ImpactAssessmentListProps {
  riskAssessmentId: number;
}

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

export function ImpactAssessmentList({ riskAssessmentId }: ImpactAssessmentListProps) {
  const { data: assessments, isLoading, isError } = useImpactAssessments(riskAssessmentId);
  const createAssessment = useCreateImpactAssessment(riskAssessmentId);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading impact assessments...</p>;
  if (isError || !assessments) return <p>Failed to load impact assessments.</p>;

  const handleCreate = async () => {
    setError(null);
    try {
      const created = await createAssessment.mutateAsync({});
      setExpandedId(created.id);
    } catch (err) {
      setError(readError(err, "Failed to create impact assessment"));
    }
  };

  // Most recently created shown first -- and expanded by default, since
  // that's the one someone opening this page most likely wants.
  const sorted = [...assessments].sort((a, b) => b.id - a.id);

  return (
    <div className="impact-assessment-list">
      {error && <p role="alert">{error}</p>}

      <button onClick={handleCreate} disabled={createAssessment.isPending}>
        {createAssessment.isPending ? "Creating..." : "New Impact Assessment"}
      </button>

      {sorted.length === 0 && <p>No impact assessments yet for this AI system.</p>}

      {sorted.map((assessment, index) => {
        const isExpanded = expandedId === null ? index === 0 : expandedId === assessment.id;
        return (
          <div key={assessment.id} className="impact-assessment-card">
            <button
              className="impact-assessment-card-header"
              onClick={() => setExpandedId(isExpanded ? -1 : assessment.id)}
            >
              <span>
                Impact Assessment #{assessment.id} &mdash; {assessment.status}
                {assessment.assessment_date ? ` (${assessment.assessment_date})` : ""}
                {assessment.next_review_date && (
                  <span
                    className={`impact-review-chip${assessment.review_overdue ? " is-overdue" : ""}`}
                  >
                    {assessment.review_overdue ? "Review overdue" : "Review due"}{" "}
                    {assessment.next_review_date}
                  </span>
                )}
              </span>
              <span>{isExpanded ? "▲" : "▼"}</span>
            </button>
            {isExpanded && (
              <ImpactAssessmentForm
                riskAssessmentId={riskAssessmentId}
                assessment={assessment}
                onDeleted={() => setExpandedId(null)}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

import { Link } from "react-router-dom";

import { useImpactAssessments } from "../hooks";
import { ImpactAssessmentForm } from "./ImpactAssessmentForm";

interface ImpactAssessmentListProps {
  riskAssessmentId: number;
}

/** The one impact assessment for this risk assessment's AI system. A risk
 * assessment can only exist once its system's impact assessment is complete,
 * so there is always exactly one here and nothing to create. */
export function ImpactAssessmentList({ riskAssessmentId }: ImpactAssessmentListProps) {
  const { data: assessments, isLoading, isError } = useImpactAssessments(riskAssessmentId);

  if (isLoading) return <p>Loading impact assessment...</p>;
  if (isError || !assessments) return <p>Failed to load impact assessment.</p>;

  const assessment = assessments[0];
  if (!assessment) return <p>No impact assessment for this AI system.</p>;

  return (
    <div className="impact-assessment-card">
      <div className="impact-assessment-card-header">
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
        <Link to={`/impact-assessments/${assessment.id}`}>Open full page</Link>
      </div>
      <ImpactAssessmentForm
        riskAssessmentId={riskAssessmentId}
        assessment={assessment}
        // Deleting from here would strand the risk assessment, so the form's
        // delete action is only offered on the impact assessment's own page.
        allowDelete={false}
        onDeleted={() => undefined}
      />
    </div>
  );
}

import { useNavigate, useParams } from "react-router-dom";

import { useAISystemInventoryRows } from "../features/ai-system-inventory/hooks";
import { ImpactAssessmentForm } from "../features/impact-assessments/components/ImpactAssessmentForm";
import { useImpactAssessment } from "../features/impact-assessments/hooks";

export function ImpactAssessmentDetailPage() {
  const { impactAssessmentId } = useParams();
  const navigate = useNavigate();
  const id = Number(impactAssessmentId);
  const { data: assessment, isLoading, isError } = useImpactAssessment(id);
  const { data: inventory } = useAISystemInventoryRows();

  if (isLoading) return <p>Loading impact assessment...</p>;
  if (isError || !assessment) return <p>Failed to load impact assessment.</p>;

  const row = inventory?.rows.find((r) => r.id === assessment.ai_system_row_id);
  const systemName =
    row && typeof row.data.name === "string" && row.data.name
      ? row.data.name
      : `AI System #${assessment.ai_system_row_id}`;

  return (
    <article>
      <div className="page-header">
        <div>
          <h1>Impact Assessment #{assessment.id}</h1>
          <p>AI System: {systemName}</p>
        </div>
      </div>

      {/* No risk assessment context here -- an impact assessment is performed
          before one exists for the system. */}
      <ImpactAssessmentForm
        riskAssessmentId={null}
        assessment={assessment}
        onDeleted={() => navigate("/risk-assessments")}
      />
    </article>
  );
}

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { useCanApproveAsOwner } from "../../audit-log/useCanApproveAsOwner";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  riskAssessmentKey,
  useApproveRiskAssessmentCaigoStage,
  useApproveRiskAssessmentOwnerStage,
  useSubmitRiskAssessmentForOwnerApproval,
  useUpdateRiskAssessment,
} from "../hooks";
import type { RiskAssessment, RiskAssessmentStatus } from "../types";

interface RiskAssessmentHeaderProps {
  riskAssessment: RiskAssessment;
  aiSystemName: string;
}

const PRE_APPROVAL_STATUSES = new Set<RiskAssessmentStatus>(["draft", "in_progress"]);

function ApprovalWorkflow({ riskAssessment }: { riskAssessment: RiskAssessment }) {
  const submit = useSubmitRiskAssessmentForOwnerApproval(riskAssessment.id);
  const approveOwnerStage = useApproveRiskAssessmentOwnerStage(riskAssessment.id);
  const approveCaigoStage = useApproveRiskAssessmentCaigoStage(riskAssessment.id);
  const ownerApproval = useCanApproveAsOwner(
    "RiskAssessmentOwnerApproval",
    riskAssessment.id,
    riskAssessment.ai_system_row_id,
  );
  const caigoApproval = useCanApprove("RiskAssessmentCaigoApproval", riskAssessment.id);

  if (PRE_APPROVAL_STATUSES.has(riskAssessment.status)) {
    return (
      <button onClick={() => submit.mutate()} disabled={submit.isPending}>
        {submit.isPending ? "Submitting..." : "Submit for Approval"}
      </button>
    );
  }
  if (riskAssessment.status === "pending_owner_approval") {
    return ownerApproval.canApprove ? (
      <button onClick={() => approveOwnerStage.mutate()} disabled={approveOwnerStage.isPending}>
        {approveOwnerStage.isPending ? "Approving..." : "Approve"}
      </button>
    ) : (
      <p className="approval-note">{ownerApproval.reason}</p>
    );
  }
  if (riskAssessment.status === "pending_caigo_approval") {
    return caigoApproval.canApprove ? (
      <button onClick={() => approveCaigoStage.mutate()} disabled={approveCaigoStage.isPending}>
        {approveCaigoStage.isPending ? "Approving..." : "Approve"}
      </button>
    ) : (
      <p className="approval-note">{caigoApproval.reason}</p>
    );
  }
  return null;
}

export function RiskAssessmentHeader({ riskAssessment, aiSystemName }: RiskAssessmentHeaderProps) {
  const updateRiskAssessment = useUpdateRiskAssessment(riskAssessment.id);
  const { data: directory } = useUserDirectory();

  return (
    <div className="risk-header">
      <p>AI System: {aiSystemName}</p>
      <div className="risk-header-row">
        <span>Status</span>
        <StatusBadge status={riskAssessment.status} />
        {PRE_APPROVAL_STATUSES.has(riskAssessment.status) && (
          <select
            aria-label="Work status"
            value={riskAssessment.status}
            onChange={(e) =>
              updateRiskAssessment.mutate({ status: e.target.value as RiskAssessmentStatus })
            }
          >
            <option value="draft">Draft</option>
            <option value="in_progress">In Progress</option>
          </select>
        )}
        <ApprovalWorkflow riskAssessment={riskAssessment} />
      </div>
      <div className="risk-header-row">
        <label htmlFor="risk-assessment-assessor">Assessor</label>
        <select
          id="risk-assessment-assessor"
          value={riskAssessment.assessor_id ?? ""}
          onChange={(e) =>
            updateRiskAssessment.mutate({
              assessor_id: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
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

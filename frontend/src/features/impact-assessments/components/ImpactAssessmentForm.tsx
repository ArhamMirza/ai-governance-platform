import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { DraftWithAiButton } from "../../ai-assist/components/DraftWithAiButton";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { ApprovalWithdrawalNotice } from "../../audit-log/ApprovalWithdrawalNotice";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { useCanApproveAsOwner } from "../../audit-log/useCanApproveAsOwner";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useApproveImpactAssessmentCaigoStage,
  useApproveImpactAssessmentOwnerStage,
  useDeleteImpactAssessment,
  useSubmitImpactAssessmentForOwnerApproval,
  useUpdateImpactAssessment,
} from "../hooks";
import { IMPACT_FACTORS } from "../impactFactors";
import type { ImpactAssessment, ImpactAssessmentUpdateInput, ImpactFactorAssessment } from "../types";
import { ImpactFactorCard } from "./ImpactFactorCard";

const ENTITY_TYPE = "ImpactAssessment";

const NARRATIVE_FIELDS: { key: keyof ImpactAssessmentUpdateInput; label: string }[] = [
  { key: "system_description", label: "System Description" },
  { key: "intended_purpose", label: "Intended Purpose" },
  { key: "foreseeable_misuse", label: "Foreseeable Misuse" },
  { key: "data_and_model_info", label: "Data & Model Information" },
  { key: "deployment_environment", label: "Deployment Environment" },
  { key: "affected_interested_parties", label: "Affected Interested Parties" },
  { key: "human_oversight_role", label: "Role of Human Oversight" },
  { key: "conclusion", label: "Conclusion" },
];

interface ImpactAssessmentFormProps {
  riskAssessmentId: number | null;
  assessment: ImpactAssessment;
  onDeleted: () => void;
  /** Hidden where deleting would strand a dependent risk assessment. */
  allowDelete?: boolean;
}

function NarrativeField({
  fieldKey,
  kind,
  impactAssessmentId,
  label,
  value,
  onSave,
}: {
  fieldKey: string;
  /** The assessment column this field fills, which is also what the model
   * is asked to draft. */
  kind: string;
  impactAssessmentId: number;
  label: string;
  value: string;
  onSave: (value: string) => void;
}) {
  const [text, setText] = useState(value);
  return (
    <div className="impact-assessment-field">
      <label htmlFor={`impact-${fieldKey}`}>{label}</label>
      <textarea
        id={`impact-${fieldKey}`}
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => text !== value && onSave(text)}
      />
      {/* A draft lands in `text`, the same state typing lands in -- so it
          saves the way any edit does, on blur, once the person has read it. */}
      <DraftWithAiButton
        kind={kind}
        impactAssessmentId={impactAssessmentId}
        onDraft={setText}
      />
    </div>
  );
}

function ApprovalWorkflow({
  riskAssessmentId,
  assessment,
}: {
  riskAssessmentId: number | null;
  assessment: ImpactAssessment;
}) {
  const submit = useSubmitImpactAssessmentForOwnerApproval(riskAssessmentId, assessment.id);
  const approveOwnerStage = useApproveImpactAssessmentOwnerStage(riskAssessmentId, assessment.id);
  const approveCaigoStage = useApproveImpactAssessmentCaigoStage(riskAssessmentId, assessment.id);
  const ownerApproval = useCanApproveAsOwner(
    "ImpactAssessmentOwnerApproval",
    assessment.id,
    assessment.ai_system_row_id,
  );
  const caigoApproval = useCanApprove("ImpactAssessmentCaigoApproval", assessment.id);
  const [error, setError] = useState<string | null>(null);

  // The server refuses an assessment that isn't fully written up and says
  // exactly what's missing -- that message is the whole point of the refusal,
  // so it's shown as-is rather than swallowed.
  const run = async (mutation: { mutateAsync: () => Promise<unknown> }, fallback: string) => {
    setError(null);
    try {
      await mutation.mutateAsync();
    } catch (err) {
      setError(readError(err, fallback));
    }
  };
  const errorAlert = error && <p role="alert">{error}</p>;

  if (assessment.status === "draft") {
    return (
      <>
        {errorAlert}
        <button
          onClick={() => run(submit, "Failed to submit for approval")}
          disabled={submit.isPending}
        >
          {submit.isPending ? "Submitting..." : "Submit for Approval"}
        </button>
      </>
    );
  }
  if (assessment.status === "pending_owner_approval") {
    return ownerApproval.canApprove ? (
      <>
        {errorAlert}
        <button
          onClick={() => run(approveOwnerStage, "Failed to approve")}
          disabled={approveOwnerStage.isPending}
        >
          {approveOwnerStage.isPending ? "Approving..." : "Approve"}
        </button>
      </>
    ) : (
      <p className="approval-note">{ownerApproval.reason}</p>
    );
  }
  if (assessment.status === "pending_caigo_approval") {
    return caigoApproval.canApprove ? (
      <>
        {errorAlert}
        <button
          onClick={() => run(approveCaigoStage, "Failed to approve")}
          disabled={approveCaigoStage.isPending}
        >
          {approveCaigoStage.isPending ? "Approving..." : "Approve"}
        </button>
      </>
    ) : (
      <p className="approval-note">{caigoApproval.reason}</p>
    );
  }
  return null;
}

export function ImpactAssessmentForm({
  riskAssessmentId,
  assessment,
  onDeleted,
  allowDelete = true,
}: ImpactAssessmentFormProps) {
  const updateAssessment = useUpdateImpactAssessment(riskAssessmentId, assessment.id);
  const deleteAssessment = useDeleteImpactAssessment(riskAssessmentId);
  const { data: directory } = useUserDirectory();
  const [error, setError] = useState<string | null>(null);

  const save = async (data: ImpactAssessmentUpdateInput) => {
    setError(null);
    try {
      await updateAssessment.mutateAsync(data);
    } catch (err) {
      setError(readError(err, "Failed to save impact assessment"));
    }
  };

  const handleDelete = async () => {
    setError(null);
    try {
      await deleteAssessment.mutateAsync(assessment.id);
      onDeleted();
    } catch (err) {
      setError(readError(err, "Failed to delete impact assessment"));
    }
  };

  const orderedFactors = IMPACT_FACTORS.map((factor) =>
    assessment.factors.find((f) => f.factor === factor),
  ).filter((f): f is ImpactFactorAssessment => f !== undefined);
  const scoredCount = orderedFactors.filter((f) => f.score !== null).length;

  return (
    <div className="impact-assessment-form">
      {error && <p role="alert">{error}</p>}
      <ApprovalWithdrawalNotice status={assessment.status} />

      <div className="impact-assessment-field">
        <span>Status</span>
        <StatusBadge status={assessment.status} />
        <ApprovalWorkflow riskAssessmentId={riskAssessmentId} assessment={assessment} />
        <p className="impact-assessment-progress">
          {assessment.next_review_date
            ? `Completed ${assessment.assessment_date ?? "—"} · next review due ${assessment.next_review_date}`
            : "Completing this (Implementation Team submits, the AI System Owner approves, then the Chief AI Governance Officer signs off) sets its review date one year out and unlocks risk assessment for this AI system."}
        </p>
      </div>

      <div className="impact-assessment-field">
        <label htmlFor={`impact-assessor-${assessment.id}`}>Assessor</label>
        <select
          id={`impact-assessor-${assessment.id}`}
          value={assessment.assessor_id ?? ""}
          onChange={(e) =>
            save({ assessor_id: e.target.value ? Number(e.target.value) : null })
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

      {NARRATIVE_FIELDS.map(({ key, label }) => (
        <NarrativeField
          key={key}
          fieldKey={`${assessment.id}-${key}`}
          kind={key}
          impactAssessmentId={assessment.id}
          label={label}
          value={(assessment[key as keyof ImpactAssessment] as string | null) ?? ""}
          onSave={(value) => save({ [key]: value } as ImpactAssessmentUpdateInput)}
        />
      ))}

      <h4>Impact Factors</h4>
      <p className="impact-assessment-progress">
        {scoredCount} of {orderedFactors.length} factors scored. Write the benefits and harms
        for a factor before scoring it.
      </p>
      <div className="impact-factor-grid">
        {orderedFactors.map((factor) => (
          <ImpactFactorCard
            key={factor.id}
            riskAssessmentId={riskAssessmentId}
            impactAssessmentId={assessment.id}
            factorAssessment={factor}
          />
        ))}
      </div>

      <h4>Framework Tags</h4>
      <FrameworkTagPicker entityType={ENTITY_TYPE} entityId={assessment.id} />

      <h4>Evidence</h4>
      <DocumentBrowser entityType={ENTITY_TYPE} entityId={assessment.id} />

      <h4>Audit Log</h4>
      <AuditLogViewer entityType={ENTITY_TYPE} entityId={assessment.id} />

      {allowDelete && (
        <button onClick={handleDelete} disabled={deleteAssessment.isPending}>
          {deleteAssessment.isPending ? "Deleting..." : "Delete Impact Assessment"}
        </button>
      )}
    </div>
  );
}

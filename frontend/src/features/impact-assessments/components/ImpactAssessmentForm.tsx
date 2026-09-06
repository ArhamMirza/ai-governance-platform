import { useState } from "react";

import { ApiError } from "../../../shared/api/httpClient";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useDeleteImpactAssessment, useUpdateImpactAssessment } from "../hooks";
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

function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}

function NarrativeField({
  fieldKey,
  label,
  value,
  onSave,
}: {
  fieldKey: string;
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
    </div>
  );
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

      <div className="impact-assessment-field">
        <label htmlFor={`impact-status-${assessment.id}`}>Status</label>
        <select
          id={`impact-status-${assessment.id}`}
          value={assessment.status}
          onChange={(e) => save({ status: e.target.value as "draft" | "completed" })}
        >
          <option value="draft">Draft</option>
          <option value="completed">Completed</option>
        </select>
        <p className="impact-assessment-progress">
          {assessment.next_review_date
            ? `Completed ${assessment.assessment_date ?? "—"} · next review due ${assessment.next_review_date}`
            : "Marking this completed sets its review date one year out, and unlocks risk assessment for this AI system."}
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

      {allowDelete && (
        <button onClick={handleDelete} disabled={deleteAssessment.isPending}>
          {deleteAssessment.isPending ? "Deleting..." : "Delete Impact Assessment"}
        </button>
      )}
    </div>
  );
}

import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useAiAssistStatus, useDraftField } from "../hooks";

interface DraftWithAiButtonProps {
  kind: string;
  impactAssessmentId: number;
  factor?: string;
  /** Where the draft goes: the caller's own field state, exactly where that
   * person's typing lands. Nothing here saves anything. */
  onDraft: (text: string) => void;
  label?: string;
}

/**
 * Drafts one field with the configured model and hands the text back.
 *
 * It deliberately does not save. The draft lands in the field's own state,
 * unsaved, for the person to read, edit or discard -- and it reaches the
 * record only by the same save they'd do after typing it themselves. That
 * keeps every approval and gate in the app exactly where it already is.
 *
 * Renders nothing at all when no provider is configured, rather than
 * offering a button that could only fail.
 */
export function DraftWithAiButton({
  kind,
  impactAssessmentId,
  factor,
  onDraft,
  label = "Draft with AI",
}: DraftWithAiButtonProps) {
  const { data: status } = useAiAssistStatus();
  const draft = useDraftField();
  const [error, setError] = useState<string | null>(null);
  const [findings, setFindings] = useState<string[]>([]);

  if (!status?.available) return null;

  const run = async () => {
    setError(null);
    setFindings([]);
    try {
      const result = await draft.mutateAsync({
        kind,
        impact_assessment_id: impactAssessmentId,
        factor,
      });
      onDraft(result.draft);
      setFindings(result.injection_findings);
    } catch (err) {
      setError(readError(err, "Couldn't draft this one"));
    }
  };

  return (
    <div className="ai-draft">
      <button type="button" className="ai-draft-button" onClick={run} disabled={draft.isPending}>
        {draft.isPending ? "Drafting..." : label}
      </button>
      {error && <span className="ai-draft-error">{error}</span>}
      {findings.length > 0 && (
        // Text in the record aimed at the model is a governance finding in
        // its own right, so it is shown rather than quietly handled.
        <span className="ai-draft-warning" role="status">
          This record contains text written to instruct an AI ({findings[0]}
          {findings.length > 1 ? `, +${findings.length - 1} more` : ""}). It was quoted to the
          model as data, not followed — worth a look.
        </span>
      )}
    </div>
  );
}

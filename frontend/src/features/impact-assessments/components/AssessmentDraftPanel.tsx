import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import { useGenerateAssessmentDraft, useLatestAssessmentDraft } from "../aiDraft";
import type { ImpactAssessment } from "../types";
import { AssessmentDraftReview } from "./AssessmentDraftReview";

/**
 * Where a person asks for the whole assessment to be drafted, and reviews it.
 *
 * Hidden entirely when no AI provider is configured, like every AI surface.
 * A draft waiting for a decision is reopened on its own -- a review can take
 * a while, and reloading the page shouldn't lose it.
 */
export function AssessmentDraftPanel({
  riskAssessmentId,
  assessment,
}: {
  riskAssessmentId: number | null;
  assessment: ImpactAssessment;
}) {
  const { data: status } = useAiAssistStatus();
  const available = status?.available === true;
  const latest = useLatestAssessmentDraft(assessment.id, available);
  const generate = useGenerateAssessmentDraft(assessment.id);
  const [error, setError] = useState<string | null>(null);

  if (!available) return null;

  if (latest.data) {
    return (
      <AssessmentDraftReview
        // A new draft is a new review; don't carry the last one's ticks over.
        key={latest.data.id}
        riskAssessmentId={riskAssessmentId}
        assessment={assessment}
        draft={latest.data}
      />
    );
  }

  const onGenerate = async () => {
    setError(null);
    try {
      await generate.mutateAsync();
    } catch (err) {
      setError(readError(err, "Couldn’t draft the assessment"));
    }
  };

  return (
    <section className="draft-launch" aria-label="Draft with AI">
      <div className="draft-launch-copy">
        <h4 className="draft-review-title">Draft the whole assessment with AI</h4>
        <p>
          Drafts every section and all eight impact factors from this AI system’s record, the
          documents filed against it, and your organisation’s policies, procedures, data
          inventory and governance roles. Each field cites what it rests on, and where the
          records don’t say, it tells you what’s missing instead of guessing. Nothing is saved
          until you review it.
        </p>
      </div>
      <button type="button" onClick={onGenerate} disabled={generate.isPending || latest.isLoading}>
        {generate.isPending ? "Drafting — this can take a minute…" : "Draft with AI"}
      </button>
      {generate.isPending && (
        <p className="assistant-working" role="status">
          <span className="assistant-working-dot" aria-hidden="true" />
          Reading the record and writing each section…
        </p>
      )}
      {error && (
        <p className="assistant-flag assistant-flag-danger" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import { useGenerateRiskSuggestions, useLatestRiskSuggestions } from "../aiRiskSuggestions";
import { RiskSuggestionReview } from "./RiskSuggestionReview";

/**
 * Where a person asks for candidate risk items to be suggested from the
 * completed impact assessment, and reviews them.
 *
 * Hidden entirely when no AI provider is configured, like every AI surface.
 * Suggestions waiting for a decision are reopened on their own -- a review
 * can take a while, and reloading the page shouldn't lose it.
 */
export function RiskSuggestionPanel({ riskAssessmentId }: { riskAssessmentId: number }) {
  const { data: status } = useAiAssistStatus();
  const available = status?.available === true;
  const latest = useLatestRiskSuggestions(riskAssessmentId, available);
  const generate = useGenerateRiskSuggestions(riskAssessmentId);
  const [error, setError] = useState<string | null>(null);

  if (!available) return null;

  if (latest.data) {
    return (
      <RiskSuggestionReview
        // A new suggestion set is a new review; don't carry the last one's
        // ticks over.
        key={latest.data.id}
        riskAssessmentId={riskAssessmentId}
        draft={latest.data}
      />
    );
  }

  const onGenerate = async (instructions: string) => {
    setError(null);
    try {
      await generate.mutateAsync(instructions || undefined);
    } catch (err) {
      setError(readError(err, "Couldn’t suggest risk items"));
    }
  };

  return (
    <section className="draft-launch" aria-label="Suggest risk items with AI">
      <div className="draft-launch-copy">
        <h4 className="draft-review-title">Suggest risk items with AI</h4>
        <p>
          Proposes candidate risk items from this AI system’s impact assessment and record,
          citing what each one rests on. Never a score -- likelihood and impact are proposed, and
          the score is always computed from them, the same as when you type a risk item by hand.
          Nothing is added until you review it.
        </p>
      </div>
      <DraftGuidanceField
        label="Guidance (optional)"
        placeholder="e.g. Focus on data leakage and third-party access risks."
        submitLabel="Suggest risk items"
        pendingLabel="Reading the record…"
        isPending={generate.isPending || latest.isLoading}
        onSubmit={onGenerate}
      />
      {generate.isPending && (
        <p className="assistant-working" role="status">
          <span className="assistant-working-dot" aria-hidden="true" />
          Reading the impact assessment and the system’s record…
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

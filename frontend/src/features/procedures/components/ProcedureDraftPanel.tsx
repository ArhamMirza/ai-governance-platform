import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import { useGenerateProcedureDraft, useLatestProcedureDraft } from "../aiDraft";
import type { Procedure } from "../types";
import { ProcedureDraftReview } from "./ProcedureDraftReview";

/**
 * Where a person asks for the procedure's title and description to be
 * drafted, and reviews it.
 *
 * Hidden entirely when no AI provider is configured, like every AI surface,
 * and also once the procedure has left draft status --
 * procedure_service.update_procedure refuses an edit outside draft, so
 * there is nothing here to offer.
 */
export function ProcedureDraftPanel({ procedure }: { procedure: Procedure }) {
  const { data: status } = useAiAssistStatus();
  const available = status?.available === true && procedure.status === "draft";
  const latest = useLatestProcedureDraft(procedure.id, available);
  const generate = useGenerateProcedureDraft(procedure.id);
  const [error, setError] = useState<string | null>(null);

  if (!available) return null;

  if (latest.data) {
    return (
      // A new draft is a new review; don't carry the last one's ticks over.
      <ProcedureDraftReview key={latest.data.id} procedure={procedure} draft={latest.data} />
    );
  }

  const onGenerate = async (instructions: string) => {
    setError(null);
    try {
      await generate.mutateAsync(instructions || undefined);
    } catch (err) {
      setError(readError(err, "Couldn’t draft the procedure"));
    }
  };

  return (
    <section className="draft-launch" aria-label="Draft with AI">
      <div className="draft-launch-copy">
        <h4 className="draft-review-title">Draft with AI</h4>
        <p>
          Drafts the title and description from the Annex A controls tagged to this procedure,
          the policy it implements, your organisation’s context and governance roles, and other
          policies and procedures on record. Each field cites what it rests on. This is also the
          first place you can edit these fields after creating the procedure -- nothing is saved
          until you review it.
        </p>
      </div>
      <DraftGuidanceField
        label="Guidance (optional)"
        placeholder="e.g. Emphasize the sign-off steps; keep it under two paragraphs."
        submitLabel="Draft with AI"
        pendingLabel="Drafting…"
        isPending={generate.isPending || latest.isLoading}
        onSubmit={onGenerate}
      />
      {generate.isPending && (
        <p className="assistant-working" role="status">
          <span className="assistant-working-dot" aria-hidden="true" />
          Reading tagged controls, the parent policy and the organisation’s context…
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

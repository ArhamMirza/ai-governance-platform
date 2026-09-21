import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  useGenerateOrganizationContextDraft,
  useLatestOrganizationContextDraft,
} from "../aiDraft";
import type { OrganizationContext } from "../types";
import { OrganizationContextDraftReview } from "./OrganizationContextDraftReview";

/**
 * Where a person asks for the organization's context to be drafted, and
 * reviews it.
 *
 * Hidden entirely when no AI provider is configured, like every AI surface.
 * A draft waiting for a decision is reopened on its own -- a review can take
 * a while, and reloading the page shouldn't lose it.
 *
 * Takes the current record as a prop rather than fetching it itself: the
 * parent has already loaded it by the time this mounts (it renders after
 * its own loading check), so the review's initial ticks -- computed once,
 * on mount -- see real data immediately instead of racing a fresh fetch.
 */
export function OrganizationContextDraftPanel({ context }: { context: OrganizationContext }) {
  const { data: status } = useAiAssistStatus();
  const available = status?.available === true;
  const latest = useLatestOrganizationContextDraft(available);
  const generate = useGenerateOrganizationContextDraft();
  const [error, setError] = useState<string | null>(null);

  if (!available) return null;

  if (latest.data) {
    return (
      <OrganizationContextDraftReview
        // A new draft is a new review; don't carry the last one's ticks over.
        key={latest.data.id}
        draft={latest.data}
        context={context}
      />
    );
  }

  const onGenerate = async (instructions: string) => {
    setError(null);
    try {
      await generate.mutateAsync(instructions || undefined);
    } catch (err) {
      setError(readError(err, "Couldn’t draft the organization’s context"));
    }
  };

  return (
    <section className="draft-launch" aria-label="Draft with AI">
      <div className="draft-launch-copy">
        <h4 className="draft-review-title">Draft with AI</h4>
        <p>
          Drafts the organization description, its overall use of AI, and proposes internal and
          external issues and interested parties -- from every AI system in the inventory, every
          policy and procedure, and your organization’s governance roles. Each field cites what it
          rests on. Nothing is saved until you review it.
        </p>
      </div>
      <DraftGuidanceField
        label="Guidance (optional)"
        placeholder="e.g. Keep the description under two sentences; emphasize our GDPR posture."
        submitLabel="Draft with AI"
        pendingLabel="Drafting — this can take a minute…"
        isPending={generate.isPending || latest.isLoading}
        onSubmit={onGenerate}
      />
      {generate.isPending && (
        <p className="assistant-working" role="status">
          <span className="assistant-working-dot" aria-hidden="true" />
          Reading the AI system inventory, policies and procedures…
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

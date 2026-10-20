import { useState } from "react";
import { Link } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import {
  useDraftSourceReadiness,
  useGenerateOrganizationContextDraft,
  useLatestOrganizationContextDraft,
} from "../aiDraft";
import type { OrganizationContext } from "../types";
import { OrganizationContextDraftReview } from "./OrganizationContextDraftReview";

/** What the draft will read, with a nudge toward whatever is still empty: the
 * draft only states what these records say, so filling them in first is what
 * makes it good. */
function DraftReadiness() {
  const { data: sources } = useDraftSourceReadiness(true);
  if (!sources) return null;
  const empty = sources.filter((source) => source.count === 0);

  return (
    <div className="draft-readiness">
      <h5 className="draft-review-title">What the draft will read</h5>
      <ul className="plain-list">
        {sources.map((source) => (
          <li key={source.key}>
            {source.count > 0 ? (
              <>
                {source.label}: <strong>{source.count}</strong>
              </>
            ) : (
              <>
                {source.label}: <strong>none yet.</strong> {source.empty_note}{" "}
                <Link to={source.href}>Add some</Link>
              </>
            )}
          </li>
        ))}
      </ul>
      <p className="approval-note">
        {empty.length > 0
          ? "Fill these in first for a better draft. "
          : ""}
        The draft only states what these records say. Guidance you type below steers it, but it
        can&rsquo;t add facts: to get something in, record it above.
      </p>
    </div>
  );
}

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
      <DraftReadiness />
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

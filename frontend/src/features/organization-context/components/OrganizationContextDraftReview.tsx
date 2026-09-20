import { useState } from "react";
import { Link } from "react-router-dom";

import { API_BASE_URL } from "../../../shared/api/httpClient";
import { readError } from "../../../shared/api/readError";
import {
  type AcceptedContextDraft,
  type ContextDraftSource,
  type ContextProposal,
  type OrganizationContextDraft,
  useApplyOrganizationContextDraft,
  useDiscardOrganizationContextDraft,
} from "../aiDraft";
import type { OrganizationContext } from "../types";

interface Choice {
  apply: boolean;
  value: string;
  category: string;
  issue: string;
  planned_response: string;
  party: string;
  needs: string;
  expectations: string;
  requirements: string;
}

function isEmpty(value: string | null | undefined): boolean {
  return value === null || value === undefined || !value.trim();
}

function initialChoices(
  draft: OrganizationContextDraft,
  organizationDescription: string | null | undefined,
  aiUsageOverview: string | null | undefined,
): Record<string, Choice> {
  const choices: Record<string, Choice> = {};
  for (const p of draft.proposals) {
    const blank: Choice = {
      apply: false,
      value: "",
      category: "",
      issue: "",
      planned_response: "",
      party: "",
      needs: "",
      expectations: "",
      requirements: "",
    };
    if (p.kind === "narrative") {
      const current = p.field === "ai_usage_overview" ? aiUsageOverview : organizationDescription;
      const offerable = !p.withheld && !p.uncited && p.value !== null;
      choices[p.key] = { ...blank, apply: offerable && isEmpty(current), value: p.value ?? "" };
    } else if (p.kind === "issue") {
      choices[p.key] = {
        ...blank,
        apply: !p.withheld && !p.uncited && p.issue !== null,
        category: p.category ?? "",
        issue: p.issue ?? "",
        planned_response: p.planned_response ?? "",
      };
    } else {
      choices[p.key] = {
        ...blank,
        apply: !p.withheld && !p.uncited && p.party !== null,
        party: p.party ?? "",
        needs: p.needs ?? "",
        expectations: p.expectations ?? "",
        requirements: p.requirements ?? "",
      };
    }
  }
  return choices;
}

function SourceChips({ draftId, citations }: { draftId: number; citations: number[] }) {
  if (citations.length === 0) return null;
  return (
    <span className="draft-chips">
      {citations.map((n) => (
        <a
          key={n}
          className="assistant-cite"
          href={`#org-context-draft-${draftId}-source-${n}`}
          aria-label={`Source ${n}`}
        >
          {n}
        </a>
      ))}
    </span>
  );
}

function ProposalRow({
  draft,
  proposal,
  choice,
  onChange,
}: {
  draft: OrganizationContextDraft;
  proposal: ContextProposal;
  choice: Choice;
  onChange: (next: Choice) => void;
}) {
  const idFor = (field: string) => `org-context-draft-${draft.id}-${proposal.key}-${field}`;
  const offerable =
    proposal.kind === "narrative"
      ? !proposal.withheld && proposal.value !== null
      : proposal.kind === "issue"
        ? !proposal.withheld && proposal.issue !== null
        : !proposal.withheld && proposal.party !== null;

  const label =
    proposal.kind === "narrative"
      ? (proposal.label ?? "Field")
      : proposal.kind === "issue"
        ? (choice.category || "Issue")
        : choice.party || "Interested party";

  return (
    <div className={`draft-row${choice.apply ? " is-applying" : ""}`}>
      <div className="draft-row-head">
        {offerable ? (
          <label className="draft-apply">
            <input
              type="checkbox"
              checked={choice.apply}
              onChange={(e) => onChange({ ...choice, apply: e.target.checked })}
              aria-label={`Apply ${label}`}
            />
            <span className="draft-row-label">{label}</span>
          </label>
        ) : (
          <span className="draft-row-label">Withheld</span>
        )}
        {proposal.uncited && offerable && (
          <span className="draft-badge draft-badge-warning">No source cited</span>
        )}
        {!offerable && <span className="draft-badge draft-badge-neutral">Not drafted</span>}
      </div>

      {offerable && proposal.kind === "narrative" && (
        <div className="draft-proposed">
          <label className="draft-caption" htmlFor={idFor("value")}>
            Proposed
          </label>
          <textarea
            id={idFor("value")}
            rows={Math.min(8, Math.max(2, Math.ceil(choice.value.length / 70)))}
            value={choice.value}
            onChange={(e) => onChange({ ...choice, apply: true, value: e.target.value })}
          />
          <SourceChips draftId={draft.id} citations={proposal.citations} />
        </div>
      )}

      {offerable && proposal.kind === "issue" && (
        <div className="draft-proposed">
          <label className="draft-caption" htmlFor={idFor("category")}>
            Category
          </label>
          <input
            id={idFor("category")}
            type="text"
            value={choice.category}
            onChange={(e) => onChange({ ...choice, apply: true, category: e.target.value })}
          />
          <label className="draft-caption" htmlFor={idFor("issue")}>
            Issue
          </label>
          <textarea
            id={idFor("issue")}
            rows={Math.min(6, Math.max(2, Math.ceil(choice.issue.length / 70)))}
            value={choice.issue}
            onChange={(e) => onChange({ ...choice, apply: true, issue: e.target.value })}
          />
          <label className="draft-caption" htmlFor={idFor("planned_response")}>
            Planned response
          </label>
          <textarea
            id={idFor("planned_response")}
            rows={Math.min(6, Math.max(2, Math.ceil(choice.planned_response.length / 70)))}
            value={choice.planned_response}
            onChange={(e) =>
              onChange({ ...choice, apply: true, planned_response: e.target.value })
            }
          />
          <SourceChips draftId={draft.id} citations={proposal.citations} />
        </div>
      )}

      {offerable && proposal.kind === "party" && (
        <div className="draft-proposed">
          <label className="draft-caption" htmlFor={idFor("party")}>
            Interested party
          </label>
          <input
            id={idFor("party")}
            type="text"
            value={choice.party}
            onChange={(e) => onChange({ ...choice, apply: true, party: e.target.value })}
          />
          <label className="draft-caption" htmlFor={idFor("needs")}>
            Needs
          </label>
          <textarea
            id={idFor("needs")}
            rows={2}
            value={choice.needs}
            onChange={(e) => onChange({ ...choice, apply: true, needs: e.target.value })}
          />
          <label className="draft-caption" htmlFor={idFor("expectations")}>
            Expectations
          </label>
          <textarea
            id={idFor("expectations")}
            rows={2}
            value={choice.expectations}
            onChange={(e) => onChange({ ...choice, apply: true, expectations: e.target.value })}
          />
          <label className="draft-caption" htmlFor={idFor("requirements")}>
            Requirements
          </label>
          <textarea
            id={idFor("requirements")}
            rows={2}
            value={choice.requirements}
            onChange={(e) => onChange({ ...choice, apply: true, requirements: e.target.value })}
          />
          <SourceChips draftId={draft.id} citations={proposal.citations} />
        </div>
      )}

      {proposal.gap && <p className="draft-gap">{proposal.gap}</p>}
    </div>
  );
}

function SourceList({ draft }: { draft: OrganizationContextDraft }) {
  return (
    <ol className="assistant-sources" aria-label="Sources the draft drew on">
      {draft.sources.map((source: ContextDraftSource) => {
        const label = (
          <>
            <span className="assistant-source-title">{source.title}</span>
            {source.section && <span className="assistant-source-section">{source.section}</span>}
          </>
        );
        return (
          <li key={source.n} id={`org-context-draft-${draft.id}-source-${source.n}`}>
            <span className="assistant-source-number">{source.n}</span>
            <div className="assistant-source-detail">
              {source.download_evidence_id !== null ? (
                <a
                  className="assistant-source-link"
                  href={`${API_BASE_URL}/evidence/${source.download_evidence_id}/download`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {label}
                </a>
              ) : source.href ? (
                <Link className="assistant-source-link" to={source.href}>
                  {label}
                </Link>
              ) : (
                <span className="assistant-source-link">{label}</span>
              )}
              {source.read_by_ocr && (
                <span className="assistant-source-badge">Read from a scan — may be imperfect</span>
              )}
              {source.injection_findings.length > 0 && (
                <span className="assistant-source-badge">Contains text aimed at an AI</span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Reviewing the model's draft of the organization's context: narrative
 * fields, candidate issues, and candidate interested parties, together.
 *
 * Nothing here is saved until "Apply". Each item may be edited before
 * it's accepted; the server then records, per item, whether it was taken
 * as drafted or changed first.
 */
export function OrganizationContextDraftReview({
  draft,
  context,
}: {
  draft: OrganizationContextDraft;
  context: OrganizationContext;
}) {
  const [choices, setChoices] = useState(() =>
    initialChoices(draft, context.organization_description, context.ai_usage_overview),
  );
  const [error, setError] = useState<string | null>(null);
  const apply = useApplyOrganizationContextDraft();
  const discard = useDiscardOrganizationContextDraft();

  const setChoice = (key: string) => (next: Choice) =>
    setChoices((previous) => ({ ...previous, [key]: next }));

  const byKind = {
    narrative: draft.proposals.filter((p) => p.kind === "narrative"),
    issue: draft.proposals.filter((p) => p.kind === "issue"),
    party: draft.proposals.filter((p) => p.kind === "party"),
  };

  const accepted: AcceptedContextDraft = {
    narrative: byKind.narrative
      .filter((p) => choices[p.key].apply && choices[p.key].value.trim())
      .map((p) => ({ key: p.key, value: choices[p.key].value.trim() })),
    issues: byKind.issue
      .filter(
        (p) => choices[p.key].apply && choices[p.key].category.trim() && choices[p.key].issue.trim(),
      )
      .map((p) => ({
        key: p.key,
        category: choices[p.key].category.trim(),
        issue: choices[p.key].issue.trim(),
        planned_response: choices[p.key].planned_response.trim() || null,
      })),
    interested_parties: byKind.party
      .filter((p) => choices[p.key].apply && choices[p.key].party.trim())
      .map((p) => ({
        key: p.key,
        party: choices[p.key].party.trim(),
        needs: choices[p.key].needs.trim() || null,
        expectations: choices[p.key].expectations.trim() || null,
        requirements: choices[p.key].requirements.trim() || null,
      })),
  };
  const selectedCount =
    accepted.narrative.length + accepted.issues.length + accepted.interested_parties.length;

  const onApply = async () => {
    setError(null);
    try {
      await apply.mutateAsync({ draftId: draft.id, accepted });
    } catch (err) {
      setError(readError(err, "Couldn’t apply the draft"));
    }
  };

  const onDiscard = async () => {
    setError(null);
    try {
      await discard.mutateAsync(draft.id);
    } catch (err) {
      setError(readError(err, "Couldn’t discard the draft"));
    }
  };

  return (
    <section className="draft-review" aria-label="AI draft for review">
      <header className="draft-review-header">
        <div>
          <span className="assistant-eyebrow">AI draft · not saved</span>
          <h4 className="draft-review-title">Review the drafted context</h4>
          <p className="draft-review-meta">
            by {draft.model} from {draft.sources.length} sources
          </p>
        </div>
      </header>

      {(draft.injection_findings?.length ?? 0) > 0 && (
        <p className="assistant-flag assistant-flag-warning" role="status">
          A source contained text written to instruct an AI (“{draft.injection_findings![0]}”). It
          was treated as data, not followed — worth checking that document.
        </p>
      )}
      {(draft.coverage_gaps?.length ?? 0) > 0 && (
        <p className="assistant-flag assistant-flag-neutral">
          Couldn’t read {draft.coverage_gaps!.map((g) => g.filename).join(", ")}, so the draft
          doesn’t draw on {draft.coverage_gaps!.length === 1 ? "it" : "them"}.
        </p>
      )}

      <p className="draft-review-hint">
        Empty fields with a cited source are ticked. Anything already written, uncited, or
        withheld is left unticked until you choose it. Editing a proposal ticks it.
      </p>

      <div className="draft-group">
        <h5 className="draft-group-title">Organization description and use of AI</h5>
        {byKind.narrative.map((proposal) => (
          <ProposalRow
            key={proposal.key}
            draft={draft}
            proposal={proposal}
            choice={choices[proposal.key]}
            onChange={setChoice(proposal.key)}
          />
        ))}
      </div>

      <div className="draft-group">
        <h5 className="draft-group-title">Internal and external issues</h5>
        {byKind.issue.length === 0 && <p>No issues proposed.</p>}
        {byKind.issue.map((proposal) => (
          <ProposalRow
            key={proposal.key}
            draft={draft}
            proposal={proposal}
            choice={choices[proposal.key]}
            onChange={setChoice(proposal.key)}
          />
        ))}
      </div>

      <div className="draft-group">
        <h5 className="draft-group-title">Interested parties</h5>
        {byKind.party.length === 0 && <p>No interested parties proposed.</p>}
        {byKind.party.map((proposal) => (
          <ProposalRow
            key={proposal.key}
            draft={draft}
            proposal={proposal}
            choice={choices[proposal.key]}
            onChange={setChoice(proposal.key)}
          />
        ))}
      </div>

      {draft.sources.length > 0 && (
        <div className="draft-group">
          <h5 className="draft-group-title">Sources</h5>
          <SourceList draft={draft} />
        </div>
      )}

      {error && (
        <p className="assistant-flag assistant-flag-danger" role="alert">
          {error}
        </p>
      )}

      <footer className="draft-review-actions">
        <button
          type="button"
          className="draft-apply-button"
          onClick={onApply}
          disabled={selectedCount === 0 || apply.isPending}
        >
          {apply.isPending
            ? "Applying…"
            : `Apply ${selectedCount} ${selectedCount === 1 ? "item" : "items"}`}
        </button>
        <button type="button" onClick={onDiscard} disabled={discard.isPending}>
          {discard.isPending ? "Discarding…" : "Discard draft"}
        </button>
      </footer>
    </section>
  );
}

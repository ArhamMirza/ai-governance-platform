import { useState } from "react";
import { Link } from "react-router-dom";

import { API_BASE_URL } from "../../../shared/api/httpClient";
import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import {
  type AcceptedProcedureField,
  type ProcedureDraft,
  type ProcedureDraftProposal,
  useApplyProcedureDraft,
  useDiscardProcedureDraft,
  useGenerateProcedureDraft,
} from "../aiDraft";
import type { Procedure } from "../types";

interface Choice {
  apply: boolean;
  value: string;
}

function currentValueOf(procedure: Procedure, proposal: ProcedureDraftProposal): string | null {
  return (procedure[proposal.field as keyof Procedure] as string | null) ?? null;
}

function isEmpty(value: string | null): boolean {
  return value === null || !value.trim();
}

/** A field starts ticked only where the record is empty and the proposal
 * cites a source -- a draft should never overwrite what someone already
 * wrote because they clicked through, and text with no source behind it
 * waits for someone to choose it deliberately rather than riding along in a
 * bulk apply. */
function initialChoices(procedure: Procedure, draft: ProcedureDraft) {
  const choices: Record<string, Choice> = {};
  for (const proposal of draft.proposals) {
    const offerable = proposal.value !== null && !proposal.withheld;
    choices[proposal.key] = {
      apply: offerable && !proposal.uncited && isEmpty(currentValueOf(procedure, proposal)),
      value: proposal.value ?? "",
    };
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
          href={`#draft-${draftId}-source-${n}`}
          aria-label={`Source ${n}`}
        >
          {n}
        </a>
      ))}
    </span>
  );
}

function DraftRow({
  draft,
  proposal,
  current,
  choice,
  onChange,
}: {
  draft: ProcedureDraft;
  proposal: ProcedureDraftProposal;
  current: string | null;
  choice: Choice;
  onChange: (next: Choice) => void;
}) {
  const offerable = proposal.value !== null && !proposal.withheld;
  const inputId = `draft-${draft.id}-${proposal.key}`;
  const isTitle = proposal.field === "title";

  return (
    <div className={`draft-row${choice.apply ? " is-applying" : ""}`}>
      <div className="draft-row-head">
        {offerable ? (
          <label className="draft-apply">
            <input
              type="checkbox"
              checked={choice.apply}
              onChange={(e) => onChange({ ...choice, apply: e.target.checked })}
              aria-label={`Apply ${proposal.label}`}
            />
            <span className="draft-row-label">{proposal.label}</span>
          </label>
        ) : (
          <span className="draft-row-label">{proposal.label}</span>
        )}
        {proposal.uncited && offerable && (
          <span className="draft-badge draft-badge-warning">No source cited</span>
        )}
        {!offerable && <span className="draft-badge draft-badge-neutral">Not drafted</span>}
      </div>

      <div className="draft-compare">
        <div className="draft-current">
          <span className="draft-caption">Now</span>
          {isEmpty(current) ? (
            <span className="draft-empty">Empty</span>
          ) : (
            <p className="draft-current-text">{current}</p>
          )}
        </div>

        {offerable && (
          <div className="draft-proposed">
            <label className="draft-caption" htmlFor={inputId}>
              Proposed{choice.value !== proposal.value ? " (edited)" : ""}
            </label>
            {isTitle ? (
              <input
                id={inputId}
                type="text"
                value={choice.value}
                // Editing a proposal is a decision to use it.
                onChange={(e) => onChange({ apply: true, value: e.target.value })}
              />
            ) : (
              <textarea
                id={inputId}
                rows={Math.min(8, Math.max(2, Math.ceil(choice.value.length / 70)))}
                value={choice.value}
                onChange={(e) => onChange({ apply: true, value: e.target.value })}
              />
            )}
            <SourceChips draftId={draft.id} citations={proposal.citations} />
          </div>
        )}
      </div>

      {proposal.gap && <p className="draft-gap">{proposal.gap}</p>}
    </div>
  );
}

function SourceList({ draft }: { draft: ProcedureDraft }) {
  return (
    <ol className="assistant-sources" aria-label="Sources the draft drew on">
      {draft.sources.map((source) => {
        const label = (
          <>
            <span className="assistant-source-title">{source.title}</span>
            {source.section && <span className="assistant-source-section">{source.section}</span>}
          </>
        );
        return (
          <li key={source.n} id={`draft-${draft.id}-source-${source.n}`}>
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
 * Reviewing a model's draft of a procedure's title and description.
 *
 * Nothing here is saved until "Apply". Each field shows what the record says
 * now beside what the model proposes, with the sources it rests on; the
 * reviewer ticks what to keep and may edit any of it first. The server then
 * records, per field, whether it was taken as drafted or changed.
 */
export function ProcedureDraftReview({
  procedure,
  draft,
}: {
  procedure: Procedure;
  draft: ProcedureDraft;
}) {
  const [choices, setChoices] = useState(() => initialChoices(procedure, draft));
  const [error, setError] = useState<string | null>(null);
  const apply = useApplyProcedureDraft(procedure.id);
  const discard = useDiscardProcedureDraft(procedure.id);
  const revise = useGenerateProcedureDraft(procedure.id);

  const setChoice = (key: string) => (next: Choice) =>
    setChoices((previous) => ({ ...previous, [key]: next }));

  const selected: AcceptedProcedureField[] = draft.proposals
    .filter((p) => choices[p.key].apply && !p.withheld && choices[p.key].value.trim())
    .map((p) => ({ key: p.key, value: choices[p.key].value.trim() }));

  const onApply = async () => {
    setError(null);
    try {
      await apply.mutateAsync({ draftId: draft.id, accepted: selected });
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

  const onRevise = async (instructions: string) => {
    setError(null);
    try {
      await revise.mutateAsync(instructions || undefined);
    } catch (err) {
      setError(readError(err, "Couldn’t redraft"));
    }
  };

  return (
    <section className="draft-review" aria-label="AI draft for review">
      <h4 className="draft-review-title">Review the drafted procedure</h4>
      <p className="draft-review-meta">
        by {draft.provider}/{draft.model} from {draft.sources.length} sources
      </p>
      <p className="draft-review-hint">
        Empty fields with a cited source are ticked. Anything already written, uncited, or
        withheld is left unticked until you choose it. Editing a proposal ticks it.
      </p>

      <div className="draft-group">
        {draft.proposals.map((proposal) => (
          <DraftRow
            key={proposal.key}
            draft={draft}
            proposal={proposal}
            current={currentValueOf(procedure, proposal)}
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

      <div className="draft-group">
        <h5 className="draft-group-title">Not quite right?</h5>
        <DraftGuidanceField
          label="Add guidance and redraft"
          placeholder="e.g. Say more about who signs off at each step."
          submitLabel="Redraft with this guidance"
          pendingLabel="Redrafting…"
          isPending={revise.isPending}
          onSubmit={onRevise}
        />
      </div>

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
          disabled={selected.length === 0 || apply.isPending}
        >
          {apply.isPending
            ? "Applying…"
            : `Apply ${selected.length} ${selected.length === 1 ? "field" : "fields"}`}
        </button>
        <button type="button" onClick={onDiscard} disabled={discard.isPending}>
          {discard.isPending ? "Discarding…" : "Discard draft"}
        </button>
      </footer>
    </section>
  );
}

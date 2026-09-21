import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { API_BASE_URL } from "../../../shared/api/httpClient";
import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import {
  type AcceptedField,
  type AssessmentDraft,
  type DraftProposal,
  type DraftSource,
  useApplyAssessmentDraft,
  useDiscardAssessmentDraft,
  useGenerateAssessmentDraft,
} from "../aiDraft";
import { IMPACT_FACTORS } from "../impactFactors";
import type { ImpactAssessment } from "../types";

interface Choice {
  apply: boolean;
  value: string | number | null;
}

const SCORES = [1, 2, 3, 4, 5];

function currentValueOf(assessment: ImpactAssessment, proposal: DraftProposal) {
  if (proposal.section === "narrative") {
    return (assessment[proposal.field as keyof ImpactAssessment] as string | null) ?? null;
  }
  const factor = assessment.factors.find((f) => f.factor === proposal.factor);
  if (!factor) return null;
  return (factor[proposal.field as "benefits" | "harms" | "criteria" | "score"] ?? null) as
    | string
    | number
    | null;
}

function isEmpty(value: string | number | null): boolean {
  return value === null || (typeof value === "string" && !value.trim());
}

/** Fields start ticked only where the record is empty and the proposal cites
 * a source. Anything a person already wrote starts as "keep mine" -- a draft
 * should never overwrite someone's work because they clicked through -- and
 * text with no source behind it waits for someone to choose it deliberately
 * rather than riding along in a bulk apply. */
function initialChoices(assessment: ImpactAssessment, draft: AssessmentDraft) {
  const choices: Record<string, Choice> = {};
  for (const proposal of draft.proposals) {
    const offerable = proposal.value !== null && !proposal.withheld;
    choices[proposal.key] = {
      apply: offerable && !proposal.uncited && isEmpty(currentValueOf(assessment, proposal)),
      value: proposal.value,
    };
  }
  return choices;
}

function SourceChips({ draftId, citations }: { draftId: number; citations: number[] }) {
  if (citations.length === 0) return null;
  return (
    <span className="draft-chips">
      {citations.map((n) => (
        <a key={n} className="assistant-cite" href={`#draft-${draftId}-source-${n}`} aria-label={`Source ${n}`}>
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
  label,
}: {
  draft: AssessmentDraft;
  proposal: DraftProposal;
  current: string | number | null;
  choice: Choice;
  onChange: (next: Choice) => void;
  label: string;
}) {
  const offerable = proposal.value !== null && !proposal.withheld;
  const inputId = `draft-${draft.id}-${proposal.key}`;
  const isScore = proposal.field === "score";

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
            <p className="draft-current-text">{String(current)}</p>
          )}
        </div>

        {offerable && (
          <div className="draft-proposed">
            <label className="draft-caption" htmlFor={inputId}>
              Proposed{choice.value !== proposal.value ? " (edited)" : ""}
            </label>
            {isScore ? (
              <>
                <select
                  id={inputId}
                  value={String(choice.value ?? "")}
                  onChange={(e) =>
                    onChange({ apply: true, value: Number(e.target.value) })
                  }
                >
                  {SCORES.map((score) => (
                    <option key={score} value={score}>
                      {score}
                    </option>
                  ))}
                </select>
                {proposal.rationale && <p className="draft-rationale">{proposal.rationale}</p>}
              </>
            ) : (
              <textarea
                id={inputId}
                rows={Math.min(8, Math.max(2, Math.ceil(String(choice.value ?? "").length / 70)))}
                value={String(choice.value ?? "")}
                // Editing a proposal is a decision to use it.
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

function SourceList({ draft }: { draft: AssessmentDraft }) {
  return (
    <ol className="assistant-sources" aria-label="Sources the draft drew on">
      {draft.sources.map((source: DraftSource) => {
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
 * Reviewing a model's draft of the whole assessment, field by field.
 *
 * Nothing here is saved until "Apply". Each field shows what the record says
 * now beside what the model proposes, with the sources it rests on; the
 * reviewer ticks what to keep and may edit any of it first. The server then
 * records, per field, whether it was taken as drafted or changed.
 */
export function AssessmentDraftReview({
  riskAssessmentId,
  assessment,
  draft,
}: {
  riskAssessmentId: number | null;
  assessment: ImpactAssessment;
  draft: AssessmentDraft;
}) {
  const [choices, setChoices] = useState(() => initialChoices(assessment, draft));
  const [error, setError] = useState<string | null>(null);
  const apply = useApplyAssessmentDraft(riskAssessmentId, assessment.id);
  const discard = useDiscardAssessmentDraft(assessment.id);
  const revise = useGenerateAssessmentDraft(assessment.id);

  const byKey = useMemo(
    () => Object.fromEntries(draft.proposals.map((p) => [p.key, p])),
    [draft.proposals],
  );
  const narrative = draft.proposals.filter((p) => p.section === "narrative");

  const setChoice = (key: string) => (next: Choice) =>
    setChoices((previous) => ({ ...previous, [key]: next }));

  const selected: AcceptedField[] = Object.entries(choices)
    .filter(([key, choice]) => choice.apply && !byKey[key].withheld && !isEmpty(choice.value))
    .map(([key, choice]) => ({ key, value: choice.value as string | number }));

  const proposedCount = draft.proposals.filter((p) => p.value !== null && !p.withheld).length;
  const gapCount = draft.proposals.filter((p) => p.value === null).length;

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
      <header className="draft-review-header">
        <div>
          <span className="assistant-eyebrow">AI draft · not saved</span>
          <h4 className="draft-review-title">Review the drafted assessment</h4>
          <p className="draft-review-meta">
            {proposedCount} fields proposed · {gapCount} not drafted for lack of evidence · by{" "}
            {draft.model} from {draft.sources.length} sources
          </p>
        </div>
      </header>

      {assessment.status !== "draft" && (
        <p className="assistant-flag assistant-flag-warning" role="status">
          This assessment is past draft. Applying changes returns it to draft and withdraws its
          approvals — the same as editing it by hand.
        </p>
      )}
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
        Empty fields with a cited source are ticked. Anything already written, and anything with
        no source behind it, is left unticked until you choose it. Editing a proposal ticks it.
      </p>

      <div className="draft-group">
        <h5 className="draft-group-title">Assessment sections</h5>
        {narrative.map((proposal) => (
          <DraftRow
            key={proposal.key}
            draft={draft}
            proposal={proposal}
            current={currentValueOf(assessment, proposal)}
            choice={choices[proposal.key]}
            onChange={setChoice(proposal.key)}
            label={proposal.label}
          />
        ))}
      </div>

      {IMPACT_FACTORS.map((factor) => (
        <div className="draft-group" key={factor}>
          <h5 className="draft-group-title">{factor}</h5>
          {draft.proposals
            .filter((p) => p.section === "factor" && p.factor === factor)
            .map((proposal) => (
              <DraftRow
                key={proposal.key}
                draft={draft}
                proposal={proposal}
                current={currentValueOf(assessment, proposal)}
                choice={choices[proposal.key]}
                onChange={setChoice(proposal.key)}
                label={`${factor} ${proposal.label.toLowerCase()}`}
              />
            ))}
        </div>
      ))}

      <div className="draft-group">
        <h5 className="draft-group-title">Sources</h5>
        <SourceList draft={draft} />
      </div>

      <div className="draft-group">
        <h5 className="draft-group-title">Not quite right?</h5>
        <DraftGuidanceField
          label="Add guidance and redraft"
          placeholder="e.g. Say more about the human oversight in place."
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

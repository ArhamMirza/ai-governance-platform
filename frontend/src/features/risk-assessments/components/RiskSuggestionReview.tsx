import { useState } from "react";
import { Link } from "react-router-dom";

import { API_BASE_URL } from "../../../shared/api/httpClient";
import { readError } from "../../../shared/api/readError";
import { DraftGuidanceField } from "../../../shared/components/DraftGuidanceField";
import {
  type AcceptedRiskItem,
  type RiskSuggestion,
  type RiskSuggestions,
  type RiskSuggestionSource,
  useApplyRiskSuggestions,
  useDiscardRiskSuggestions,
  useGenerateRiskSuggestions,
} from "../aiRiskSuggestions";

interface Choice {
  apply: boolean;
  category: string;
  description: string;
  mitigation: string;
  likelihood: number | null;
  impact: number | null;
  risk_owner: string;
}

const SCORES = [1, 2, 3, 4, 5];

function initialChoices(draft: RiskSuggestions): Record<string, Choice> {
  const choices: Record<string, Choice> = {};
  for (const proposal of draft.proposals) {
    choices[proposal.key] = {
      // Ticked only when the suggestion has real content and a source
      // behind it -- an uncited or withheld item waits for someone to
      // choose it deliberately, the same standard drafting uses.
      apply: !proposal.withheld && !proposal.uncited && proposal.description !== null,
      category: proposal.category ?? "",
      description: proposal.description ?? "",
      mitigation: proposal.mitigation ?? "",
      likelihood: proposal.likelihood,
      impact: proposal.impact,
      risk_owner: "",
    };
  }
  return choices;
}

function ScoreSelect({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: number | null;
  onChange: (next: number | null) => void;
}) {
  return (
    <label className="draft-caption" htmlFor={id}>
      {label}
      <select
        id={id}
        value={value === null ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      >
        <option value="">Not set</option>
        {SCORES.map((score) => (
          <option key={score} value={score}>
            {score}
          </option>
        ))}
      </select>
    </label>
  );
}

function SourceChips({ draftId, citations }: { draftId: number; citations: number[] }) {
  if (citations.length === 0) return null;
  return (
    <span className="draft-chips">
      {citations.map((n) => (
        <a
          key={n}
          className="assistant-cite"
          href={`#risk-suggestion-${draftId}-source-${n}`}
          aria-label={`Source ${n}`}
        >
          {n}
        </a>
      ))}
    </span>
  );
}

function SuggestionRow({
  draft,
  proposal,
  choice,
  onChange,
}: {
  draft: RiskSuggestions;
  proposal: RiskSuggestion;
  choice: Choice;
  onChange: (next: Choice) => void;
}) {
  const offerable = !proposal.withheld && proposal.description !== null;
  const idFor = (field: string) => `risk-suggestion-${draft.id}-${proposal.key}-${field}`;

  return (
    <div className={`draft-row${choice.apply ? " is-applying" : ""}`}>
      <div className="draft-row-head">
        {offerable ? (
          <label className="draft-apply">
            <input
              type="checkbox"
              checked={choice.apply}
              onChange={(e) => onChange({ ...choice, apply: e.target.checked })}
              aria-label={`Add ${proposal.category ?? "this risk item"}`}
            />
            <span className="draft-row-label">{proposal.category ?? "Risk item"}</span>
          </label>
        ) : (
          <span className="draft-row-label">Withheld suggestion</span>
        )}
        {proposal.uncited && offerable && (
          <span className="draft-badge draft-badge-warning">No source cited</span>
        )}
        {!offerable && <span className="draft-badge draft-badge-neutral">Withheld</span>}
      </div>

      {offerable && (
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

          <label className="draft-caption" htmlFor={idFor("description")}>
            Description
          </label>
          <textarea
            id={idFor("description")}
            rows={Math.min(8, Math.max(2, Math.ceil(choice.description.length / 70)))}
            value={choice.description}
            onChange={(e) => onChange({ ...choice, apply: true, description: e.target.value })}
          />

          <label className="draft-caption" htmlFor={idFor("mitigation")}>
            Mitigation
          </label>
          <textarea
            id={idFor("mitigation")}
            rows={Math.min(6, Math.max(2, Math.ceil(choice.mitigation.length / 70)))}
            value={choice.mitigation}
            onChange={(e) => onChange({ ...choice, apply: true, mitigation: e.target.value })}
          />

          <div className="draft-score-pair">
            <ScoreSelect
              id={idFor("likelihood")}
              label="Likelihood"
              value={choice.likelihood}
              onChange={(next) => onChange({ ...choice, apply: true, likelihood: next })}
            />
            <ScoreSelect
              id={idFor("impact")}
              label="Impact"
              value={choice.impact}
              onChange={(next) => onChange({ ...choice, apply: true, impact: next })}
            />
          </div>
          <p className="draft-review-hint">
            The risk score is always computed from likelihood and impact when the item is added,
            not taken from the AI.
          </p>

          <label className="draft-caption" htmlFor={idFor("owner")}>
            Risk owner (optional -- never proposed by the AI)
          </label>
          <input
            id={idFor("owner")}
            type="text"
            value={choice.risk_owner}
            onChange={(e) => onChange({ ...choice, risk_owner: e.target.value })}
          />

          <SourceChips draftId={draft.id} citations={proposal.citations} />
        </div>
      )}

      {proposal.gap && <p className="draft-gap">{proposal.gap}</p>}
    </div>
  );
}

function SourceList({ draft }: { draft: RiskSuggestions }) {
  return (
    <ol className="assistant-sources" aria-label="Sources the suggestions drew on">
      {draft.sources.map((source: RiskSuggestionSource) => {
        const label = (
          <>
            <span className="assistant-source-title">{source.title}</span>
            {source.section && <span className="assistant-source-section">{source.section}</span>}
          </>
        );
        return (
          <li key={source.n} id={`risk-suggestion-${draft.id}-source-${source.n}`}>
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
 * Reviewing the model's candidate risk items, one by one.
 *
 * Nothing here is added until "Add selected". Each item may be edited
 * before it's added; the server then records, per item, whether it was
 * added as suggested or changed first.
 */
export function RiskSuggestionReview({
  riskAssessmentId,
  draft,
}: {
  riskAssessmentId: number;
  draft: RiskSuggestions;
}) {
  const [choices, setChoices] = useState(() => initialChoices(draft));
  const [error, setError] = useState<string | null>(null);
  const apply = useApplyRiskSuggestions(riskAssessmentId);
  const discard = useDiscardRiskSuggestions(riskAssessmentId);
  const revise = useGenerateRiskSuggestions(riskAssessmentId);

  const setChoice = (key: string) => (next: Choice) =>
    setChoices((previous) => ({ ...previous, [key]: next }));

  const selected: AcceptedRiskItem[] = Object.entries(choices)
    .filter(([, choice]) => choice.apply && choice.category.trim() && choice.description.trim())
    .map(([key, choice]) => ({
      key,
      category: choice.category.trim(),
      description: choice.description.trim(),
      mitigation: choice.mitigation.trim() || null,
      likelihood: choice.likelihood,
      impact: choice.impact,
      risk_owner: choice.risk_owner.trim() || null,
    }));

  const proposedCount = draft.proposals.filter((p) => !p.withheld).length;
  const withheldCount = draft.proposals.filter((p) => p.withheld).length;

  const onApply = async () => {
    setError(null);
    try {
      await apply.mutateAsync({ draftId: draft.id, accepted: selected });
    } catch (err) {
      setError(readError(err, "Couldn’t add the selected risk items"));
    }
  };

  const onDiscard = async () => {
    setError(null);
    try {
      await discard.mutateAsync(draft.id);
    } catch (err) {
      setError(readError(err, "Couldn’t discard the suggestions"));
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
    <section className="draft-review" aria-label="AI risk item suggestions for review">
      <header className="draft-review-header">
        <div>
          <span className="assistant-eyebrow">AI suggestions · not added</span>
          <h4 className="draft-review-title">Review the suggested risk items</h4>
          <p className="draft-review-meta">
            {proposedCount} {proposedCount === 1 ? "item" : "items"} suggested
            {withheldCount > 0 &&
              ` · ${withheldCount} withheld for lack of support`} · by {draft.model} from{" "}
            {draft.sources.length} sources
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
          Couldn’t read {draft.coverage_gaps!.map((g) => g.filename).join(", ")}, so the
          suggestions don’t draw on {draft.coverage_gaps!.length === 1 ? "it" : "them"}.
        </p>
      )}

      <p className="draft-review-hint">
        Items with a cited source are ticked to add. Anything uncited or withheld waits for you to
        choose it. Edit any field before adding -- an edited item is logged as edited, not
        as-drafted.
      </p>

      <div className="draft-group">
        {draft.proposals.map((proposal) => (
          <SuggestionRow
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

      <div className="draft-group">
        <h5 className="draft-group-title">Not quite right?</h5>
        <DraftGuidanceField
          label="Add guidance and redraft"
          placeholder="e.g. Focus more on third-party access risks."
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
            ? "Adding…"
            : `Add ${selected.length} ${selected.length === 1 ? "item" : "items"}`}
        </button>
        <button type="button" onClick={onDiscard} disabled={discard.isPending}>
          {discard.isPending ? "Discarding…" : "Discard suggestions"}
        </button>
      </footer>
    </section>
  );
}

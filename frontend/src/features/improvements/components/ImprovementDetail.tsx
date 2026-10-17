import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useCarryOutAsChange,
  useDeleteImprovement,
  useImprovement,
  useSetImprovementStatus,
  useUpdateImprovement,
} from "../hooks";
import { ACTION_LABELS, actionsFor, sourceLabel, sourcePath } from "../labels";
import type { Improvement, ImprovementAction, ImprovementUpdateInput } from "../types";
import { ImprovementFlags } from "./ImprovementList";

type TextField = "title" | "description" | "expected_benefit";

/** Which moves need a note, and what the note is for. */
const NOTE_FOR: Partial<Record<ImprovementAction, string>> = {
  implement: "What changed, and did it work?",
  decline: "Why it isn't going ahead",
};

function SourceLine({ improvement }: { improvement: Improvement }) {
  if (improvement.source_type === null || improvement.source_id === null) {
    return <p>Came from {sourceLabel(improvement.source).toLowerCase()}.</p>;
  }
  if (improvement.source_label === null) {
    return <p>Came from a record that no longer exists.</p>;
  }
  const path = sourcePath(improvement.source_type, improvement.source_id);
  return (
    <p>
      Came from{" "}
      {path ? <Link to={path}>{improvement.source_label}</Link> : improvement.source_label}.
    </p>
  );
}

export function ImprovementDetail({ improvementId }: { improvementId: number }) {
  const { data: improvement, isLoading, isError } = useImprovement(improvementId);
  const { data: directory } = useUserDirectory();
  const update = useUpdateImprovement(improvementId);
  const setStatus = useSetImprovementStatus(improvementId);
  const carryOut = useCarryOutAsChange(improvementId);
  const deleteImprovement = useDeleteImprovement();
  const navigate = useNavigate();
  const [notes, setNotes] = useState<Partial<Record<ImprovementAction, string>>>({});

  if (isLoading) return <p>Loading improvement...</p>;
  if (isError || !improvement) return <p>Failed to load improvement.</p>;

  const save = (data: ImprovementUpdateInput) => update.mutate(data);
  const actions = actionsFor(improvement.status);

  const move = async (action: ImprovementAction) => {
    // Only the moves in NOTE_FOR have a note field, so the rest send none.
    const note = (notes[action] ?? "").trim();
    await setStatus.mutateAsync({ action, note: note || null });
    setNotes({});
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${improvement.title}"?`)) return;
    await deleteImprovement.mutateAsync(improvementId);
    navigate("/improvements");
  };

  const textInput = (key: TextField, label: string, multiline: boolean) => {
    const props = {
      id: `improvement-${key}`,
      defaultValue: improvement[key] ?? "",
      onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.target.value !== (improvement[key] ?? "")) {
          // A title can't be blank; every other text field clears to null.
          if (key === "title" && !e.target.value.trim()) return;
          save({ [key]: e.target.value.trim() || null });
        }
      },
    };
    return (
      <div key={key}>
        <label htmlFor={props.id}>{label}</label>
        {multiline ? <textarea {...props} /> : <input {...props} />}
      </div>
    );
  };

  return (
    <article key={improvement.updated_at}>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{improvement.title}</h2>
          <StatusBadge status={improvement.standing.state} />
          <ImprovementFlags improvement={improvement} />
        </div>
        <p>
          Raised {improvement.raised_on} · target {improvement.target_date}
          {improvement.decided_on && ` · accepted ${improvement.decided_on}`}
          {improvement.closed_on && ` · closed ${improvement.closed_on}`}
        </p>
        <SourceLine improvement={improvement} />
      </header>

      <section>
        <h3>Progress</h3>
        {improvement.outcome && (
          <p>
            <strong>Outcome:</strong> {improvement.outcome}
          </p>
        )}
        {improvement.decline_reason && (
          <p>
            <strong>Declined:</strong> {improvement.decline_reason}
          </p>
        )}
        {actions.map((action) =>
          NOTE_FOR[action] ? (
            <div key={`note-${action}`}>
              <label htmlFor={`improvement-note-${action}`}>{NOTE_FOR[action]}</label>
              <textarea
                id={`improvement-note-${action}`}
                value={notes[action] ?? ""}
                onChange={(e) => setNotes((prev) => ({ ...prev, [action]: e.target.value }))}
              />
            </div>
          ) : null,
        )}
        <div className="detail-actions">
          {actions.map((action) => (
            <button
              key={action}
              onClick={() => move(action)}
              disabled={
                setStatus.isPending || (Boolean(NOTE_FOR[action]) && !notes[action]?.trim())
              }
            >
              {ACTION_LABELS[action]}
            </button>
          ))}
        </div>
        {setStatus.isError && (
          <p role="alert">{readError(setStatus.error, "Failed to update the improvement.")}</p>
        )}
      </section>

      <section>
        <h3>Carrying it out</h3>
        {improvement.change_id !== null ? (
          <p>
            Being carried out as{" "}
            <Link to={`/changes/${improvement.change_id}`}>a planned change</Link>.
          </p>
        ) : improvement.status === "accepted" ? (
          <div>
            <button onClick={() => carryOut.mutate()} disabled={carryOut.isPending}>
              Carry Out as a Change
            </button>
            <span className="approval-note">
              {" "}
              Plans it as a change to the management system (6.3), for its target date.
            </span>
            {carryOut.isError && (
              <p role="alert">{readError(carryOut.error, "Failed to plan the change.")}</p>
            )}
          </div>
        ) : (
          <p className="approval-note">Accept it first to plan it as a change.</p>
        )}
      </section>

      {textInput("title", "Improvement", false)}
      {textInput("description", "Description", true)}
      {textInput("expected_benefit", "Expected benefit", true)}
      <div>
        <label htmlFor="improvement-owner-edit">Owner</label>
        <select
          id="improvement-owner-edit"
          value={improvement.owner_id ?? ""}
          onChange={(e) => save({ owner_id: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="improvement-target-edit">Target date</label>
        <input
          id="improvement-target-edit"
          type="date"
          value={improvement.target_date}
          onChange={(e) => e.target.value && save({ target_date: e.target.value })}
        />
      </div>
      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the improvement.")}</p>
      )}

      <h3>Documents</h3>
      <DocumentBrowser entityType="Improvement" entityId={improvementId} />

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="Improvement" entityId={improvementId} />

      <AuditLogViewer entityType="Improvement" entityId={improvementId} />

      <div className="detail-actions">
        {improvement.status === "proposed" ? (
          <button onClick={handleDelete} disabled={deleteImprovement.isPending}>
            Delete Improvement
          </button>
        ) : (
          <p className="approval-note">
            Once decided on, an improvement stays on record. Decline it instead of deleting it.
          </p>
        )}
      </div>
    </article>
  );
}

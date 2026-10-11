import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AISystemLinkPicker } from "../../ai-systems/components/AISystemLinkPicker";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useChange,
  useDeleteChange,
  useSetChangeAISystems,
  useSetChangeStatus,
  useUpdateChange,
} from "../hooks";
import { ACTION_LABELS, CHANGE_TYPE_OPTIONS, actionsFor } from "../labels";
import type { ChangeAction, ChangeType, ChangeUpdateInput } from "../types";
import { ChangeFlags } from "./ChangeList";

type TextField = "title" | "reason" | "consequences" | "resources_needed" | "description";

const PLAN_FIELDS: { key: TextField; label: string }[] = [
  { key: "description", label: "Description" },
  { key: "reason", label: "Why" },
  { key: "consequences", label: "Potential consequences" },
  { key: "resources_needed", label: "Resources needed" },
];

export function ChangeDetail({ changeId }: { changeId: number }) {
  const { data: change, isLoading, isError } = useChange(changeId);
  const { data: directory } = useUserDirectory();
  const update = useUpdateChange(changeId);
  const setStatus = useSetChangeStatus(changeId);
  const setLinks = useSetChangeAISystems(changeId);
  const deleteChange = useDeleteChange();
  const navigate = useNavigate();
  const [note, setNote] = useState("");

  if (isLoading) return <p>Loading change...</p>;
  if (isError || !change) return <p>Failed to load change.</p>;

  const save = (data: ChangeUpdateInput) => update.mutate(data);
  const closing = (action: ChangeAction) => action === "implement" || action === "cancel";

  const move = async (action: ChangeAction) => {
    await setStatus.mutateAsync({ action, note: closing(action) ? note || null : null });
    setNote("");
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${change.title}"?`)) return;
    await deleteChange.mutateAsync(changeId);
    navigate("/changes");
  };

  const textInput = ({ key, label }: { key: TextField; label: string }, multiline: boolean) => {
    const props = {
      id: `change-${key}`,
      defaultValue: change[key] ?? "",
      onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.target.value !== (change[key] ?? "")) {
          // A title can't be blank; every other text field clears to null.
          if (key === "title" && !e.target.value) return;
          save({ [key]: e.target.value || null });
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

  const actions = actionsFor(change.status);

  return (
    <article key={change.updated_at}>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{change.title}</h2>
          <StatusBadge status={change.standing.state} />
          <ChangeFlags change={change} />
        </div>
        <p>
          Raised {change.raised_on} · planned for {change.planned_date}
          {change.started_on && ` · started ${change.started_on}`}
          {change.closed_on && ` · closed ${change.closed_on}`}
          {change.closure_note && `: ${change.closure_note}`}
        </p>
      </header>

      <section>
        <h3>Progress</h3>
        {actions.some(closing) && (
          <div>
            <label htmlFor="change-note">Note (recorded when closing)</label>
            <input id="change-note" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        )}
        <div className="detail-actions">
          {actions.map((action) => (
            <button key={action} onClick={() => move(action)} disabled={setStatus.isPending}>
              {ACTION_LABELS[action]}
            </button>
          ))}
        </div>
        {setStatus.isError && (
          <p role="alert">{readError(setStatus.error, "Failed to update the change.")}</p>
        )}
      </section>

      {textInput({ key: "title", label: "Change" }, false)}
      <div>
        <label htmlFor="change-type-edit">What it concerns</label>
        <select
          id="change-type-edit"
          value={change.change_type}
          onChange={(e) => save({ change_type: e.target.value as ChangeType })}
        >
          {CHANGE_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {PLAN_FIELDS.map((field) => textInput(field, true))}
      <div>
        <label htmlFor="change-owner-edit">Owner</label>
        <select
          id="change-owner-edit"
          value={change.owner_id ?? ""}
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
        <label htmlFor="change-raised-on-edit">Raised on</label>
        <input
          id="change-raised-on-edit"
          type="date"
          value={change.raised_on}
          onChange={(e) => e.target.value && save({ raised_on: e.target.value })}
        />
      </div>
      <div>
        <label htmlFor="change-planned-date-edit">Planned for</label>
        <input
          id="change-planned-date-edit"
          type="date"
          value={change.planned_date}
          onChange={(e) => e.target.value && save({ planned_date: e.target.value })}
        />
      </div>
      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the change.")}</p>
      )}

      <section>
        <h3>AI Systems Affected</h3>
        <AISystemLinkPicker
          idPrefix="change"
          value={change.ai_system_row_ids}
          pending={setLinks.isPending}
          onChange={(rowIds) => setLinks.mutate(rowIds)}
        />
      </section>

      <h3>Documents</h3>
      <DocumentBrowser entityType="ManagementSystemChange" entityId={changeId} />

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="ManagementSystemChange" entityId={changeId} />

      <AuditLogViewer entityType="ManagementSystemChange" entityId={changeId} />

      <div className="detail-actions">
        {change.status === "planned" ? (
          <button onClick={handleDelete} disabled={deleteChange.isPending}>
            Delete Change
          </button>
        ) : (
          <p className="approval-note">
            Once started or closed, a change stays on record. Cancel it instead of deleting it.
          </p>
        )}
      </div>
    </article>
  );
}

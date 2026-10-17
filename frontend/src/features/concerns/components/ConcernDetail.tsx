import { useState } from "react";
import { Link } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { SourceImprovements } from "../../improvements/components/SourceImprovements";
import { aiSystemName } from "../../suppliers/labels";
import { useUserDirectory } from "../../users/hooks";
import { formatUserOption } from "../../users/formatUserOption";
import {
  useConcern,
  useConcernCorrectiveActions,
  useRaiseCorrectiveActionFromConcern,
  useRaiseIncidentFromConcern,
  useSetConcernStatus,
  useUpdateConcern,
} from "../hooks";
import {
  ACTION_LABELS,
  OUTCOME_OPTIONS,
  actionsFor,
  categoryLabel,
  channelLabel,
  outcomeLabel,
} from "../labels";
import type { Concern, ConcernAction, ConcernOutcome } from "../types";

function todayPlus(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function WhoRaisedIt({ concern }: { concern: Concern }) {
  if (concern.is_anonymous) {
    return <p>Raised anonymously. Nothing that identifies who raised it is stored.</p>;
  }
  if (concern.reporter_name) return <p>Raised by {concern.reporter_name}.</p>;
  return (
    <p>
      Raised {concern.channel === "employee_portal" ? "under a name that is no longer on file" : "by"}
      {concern.reporter_note ? `: ${concern.reporter_note}` : "."}
    </p>
  );
}

function RaiseCorrectiveActionForm({ concern }: { concern: Concern }) {
  const raise = useRaiseCorrectiveActionFromConcern(concern.id);
  const { data: directory } = useUserDirectory();
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");
  const [dueDate, setDueDate] = useState(todayPlus(30));

  const submit = async () => {
    await raise.mutateAsync({
      title,
      action_description: null,
      assignee_id: Number(assignee),
      due_date: dueDate,
    });
    setTitle("");
  };

  return (
    <div className="inline-form">
      <label htmlFor="concern-ca-title">Corrective action</label>
      <input id="concern-ca-title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <label htmlFor="concern-ca-assignee">Assigned to</label>
      <select
        id="concern-ca-assignee"
        value={assignee}
        onChange={(e) => setAssignee(e.target.value)}
      >
        <option value="">Choose someone</option>
        {(directory ?? []).map((user) => (
          <option key={user.id} value={user.id}>
            {formatUserOption(user)}
          </option>
        ))}
      </select>
      <label htmlFor="concern-ca-due">Due</label>
      <input
        id="concern-ca-due"
        type="date"
        value={dueDate}
        onChange={(e) => setDueDate(e.target.value)}
      />
      <button onClick={submit} disabled={!title.trim() || !assignee || raise.isPending}>
        Raise Corrective Action
      </button>
      {raise.isError && (
        <p role="alert">{readError(raise.error, "Failed to raise the corrective action.")}</p>
      )}
    </div>
  );
}

export function ConcernDetail({ concernId }: { concernId: number }) {
  const { data: concern, isLoading, isError } = useConcern(concernId);
  const { data: inventory } = useAISystemInventoryRows();
  const { data: correctiveActions } = useConcernCorrectiveActions(concernId);
  const { data: directory } = useUserDirectory();
  const update = useUpdateConcern(concernId);
  const setStatus = useSetConcernStatus(concernId);
  const raiseIncident = useRaiseIncidentFromConcern(concernId);
  const [outcome, setOutcome] = useState<ConcernOutcome>("substantiated");
  const [note, setNote] = useState("");

  if (isLoading) return <p>Loading concern...</p>;
  if (isError || !concern) return <p>Failed to load concern.</p>;

  const actions = actionsFor(concern.status);
  const closing = (action: ConcernAction) => action === "resolve" || action === "dismiss";
  const move = async (action: ConcernAction) => {
    await setStatus.mutateAsync({
      action,
      outcome: action === "resolve" ? outcome : null,
      note: closing(action) ? note.trim() || null : null,
    });
    setNote("");
  };
  const handler = directory?.find((user) => user.id === concern.handler_id);
  const system = inventory?.rows.find((row) => row.id === concern.ai_system_row_id);

  return (
    <article key={`${concern.id}-${concern.status}`}>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{categoryLabel(concern.category)}</h2>
          <StatusBadge status={concern.status} />
          {concern.awaiting_triage && <span className="flag-chip">Not acknowledged</span>}
        </div>
        <p>
          Received {concern.received_on} · {channelLabel(concern.channel)}
          {concern.status === "received" && ` · acknowledge by ${concern.acknowledge_by}`}
          {concern.acknowledged_on && ` · acknowledged ${concern.acknowledged_on}`}
          {concern.closed_on && ` · closed ${concern.closed_on}`}
          {concern.outcome && ` · ${outcomeLabel(concern.outcome)}`}
        </p>
        <WhoRaisedIt concern={concern} />
      </header>

      <h3>What was raised</h3>
      <p>{concern.description}</p>
      <p>
        About:{" "}
        {concern.ai_system_row_id !== null ? (
          <Link to={`/ai-systems/${concern.ai_system_row_id}`}>
            {aiSystemName(system, concern.ai_system_row_id)}
          </Link>
        ) : (
          (concern.system_note ?? "no system named")
        )}
      </p>

      <section>
        <h3>Progress</h3>
        {handler && <p>Handled by {formatUserOption(handler)}.</p>}
        {actions.includes("resolve") && (
          <div>
            <label htmlFor="concern-outcome">How it turned out</label>
            <select
              id="concern-outcome"
              value={outcome}
              onChange={(e) => setOutcome(e.target.value as ConcernOutcome)}
            >
              {OUTCOME_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        )}
        {actions.some(closing) && (
          <div>
            <label htmlFor="concern-closing-note">Note (needed to close without action)</label>
            <input
              id="concern-closing-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
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
          <p role="alert">{readError(setStatus.error, "Failed to update the concern.")}</p>
        )}
        {concern.closure_note && <p>Closing note: {concern.closure_note}</p>}
      </section>

      <section>
        <h3>Reply to the person who raised it</h3>
        <p className="approval-note">
          They see this, and where the concern stands, and nothing else you write here.
        </p>
        <textarea
          aria-label="Reply to the reporter"
          defaultValue={concern.reply_to_reporter ?? ""}
          onBlur={(e) => {
            if (e.target.value !== (concern.reply_to_reporter ?? "")) {
              update.mutate({ reply_to_reporter: e.target.value || null });
            }
          }}
        />
      </section>

      <section>
        <h3>Internal notes</h3>
        <p className="approval-note">Only people handling concerns can read these.</p>
        <textarea
          aria-label="Internal notes"
          defaultValue={concern.internal_notes ?? ""}
          onBlur={(e) => {
            if (e.target.value !== (concern.internal_notes ?? "")) {
              update.mutate({ internal_notes: e.target.value || null });
            }
          }}
        />
        {update.isError && (
          <p role="alert">{readError(update.error, "Failed to save.")}</p>
        )}
      </section>

      <section>
        <h3>What it led to</h3>
        {concern.incident_id !== null ? (
          <p>
            Incident raised: <Link to={`/incidents/${concern.incident_id}`}>#{concern.incident_id}</Link>
          </p>
        ) : (
          <div>
            <button onClick={() => raiseIncident.mutate()} disabled={raiseIncident.isPending}>
              Raise as an Incident
            </button>
            <span className="approval-note">
              {" "}
              Opens an AI incident from the description -- never who raised it.
            </span>
            {raiseIncident.isError && (
              <p role="alert">
                {readError(raiseIncident.error, "Failed to raise the incident.")}
              </p>
            )}
          </div>
        )}
        {correctiveActions && correctiveActions.length > 0 && (
          <ul>
            {correctiveActions.map((action) => (
              <li key={action.id}>
                <Link to={`/corrective-actions/${action.id}`}>{action.title}</Link>{" "}
                <StatusBadge status={action.status} />
              </li>
            ))}
          </ul>
        )}
        <RaiseCorrectiveActionForm concern={concern} />
        <h4>Improvements</h4>
        <p className="approval-note">
          An improvement is readable by everyone in the organization, so it starts empty -- nothing
          of what was reported is copied into it.
        </p>
        <SourceImprovements
          from={{ sourceType: "Concern", sourceId: concern.id, label: `concern #${concern.id}` }}
        />
      </section>

      <AuditLogViewer entityType="Concern" entityId={concernId} />
    </article>
  );
}

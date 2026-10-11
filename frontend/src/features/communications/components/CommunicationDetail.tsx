import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useCommunication,
  useDeleteCommunication,
  useDeleteCommunicationRecord,
  useRecordCommunication,
  useUpdateCommunication,
} from "../hooks";
import { DIRECTION_OPTIONS, cadenceLabel } from "../labels";
import type {
  CommunicationDetail as CommunicationDetailData,
  CommunicationDirection,
  CommunicationStatus,
} from "../types";

type TextField = "topic" | "audience" | "method" | "notes";

const SHORT_FIELDS: { key: TextField; label: string }[] = [
  { key: "topic", label: "What is communicated" },
  { key: "audience", label: "To whom" },
  { key: "method", label: "How" },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Interval and first-due date are saved together -- the server refuses one
 * without the other. Both empty means done only when needed. */
function ScheduleForm({ item }: { item: CommunicationDetailData }) {
  const update = useUpdateCommunication(item.id);
  const [interval, setInterval] = useState(item.interval_months?.toString() ?? "");
  const [firstDue, setFirstDue] = useState(item.first_due ?? "");
  const complete = (interval === "") === (firstDue === "");

  return (
    <div>
      <label htmlFor="communication-interval-edit">Every (months)</label>
      <input
        id="communication-interval-edit"
        type="number"
        min={1}
        value={interval}
        onChange={(e) => setInterval(e.target.value)}
      />
      <label htmlFor="communication-first-due-edit">First due</label>
      <input
        id="communication-first-due-edit"
        type="date"
        value={firstDue}
        onChange={(e) => setFirstDue(e.target.value)}
      />
      <button
        onClick={() =>
          update.mutate({
            interval_months: interval ? Number(interval) : null,
            first_due: firstDue || null,
          })
        }
        disabled={!complete || update.isPending}
      >
        Save schedule
      </button>
      {!complete && (
        <p className="approval-note">Set both, or clear both for something done when needed.</p>
      )}
    </div>
  );
}

function RecordForm({ itemId }: { itemId: number }) {
  const record = useRecordCommunication(itemId);
  const [date, setDate] = useState(todayIso());
  const [summary, setSummary] = useState("");

  const submit = async () => {
    await record.mutateAsync({ communicated_on: date, summary: summary || null });
    setSummary("");
  };

  return (
    <div className="inline-form">
      <label htmlFor="communication-record-date">Done on</label>
      <input
        id="communication-record-date"
        type="date"
        max={todayIso()}
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />
      <label htmlFor="communication-record-summary">What was communicated</label>
      <input
        id="communication-record-summary"
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
      />
      <button onClick={submit} disabled={!date || record.isPending}>
        Record Communication
      </button>
      {record.isError && (
        <p role="alert">{readError(record.error, "Failed to record the communication.")}</p>
      )}
    </div>
  );
}

export function CommunicationDetail({ communicationId }: { communicationId: number }) {
  const { data: item, isLoading, isError } = useCommunication(communicationId);
  const { data: directory } = useUserDirectory();
  const update = useUpdateCommunication(communicationId);
  const deleteItem = useDeleteCommunication();
  const deleteRecord = useDeleteCommunicationRecord();
  const navigate = useNavigate();
  const [openEvidence, setOpenEvidence] = useState<number | null>(null);

  if (isLoading) return <p>Loading communication...</p>;
  if (isError || !item) return <p>Failed to load communication.</p>;

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${item.topic}" and its records?`)) return;
    await deleteItem.mutateAsync(communicationId);
    navigate("/communications");
  };

  const textInput = ({ key, label }: { key: TextField; label: string }, multiline: boolean) => {
    const props = {
      id: `communication-${key}`,
      defaultValue: item[key] ?? "",
      onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.target.value === (item[key] ?? "")) return;
        // The topic and audience can't be blank; the rest clear to null.
        if ((key === "topic" || key === "audience") && !e.target.value) return;
        update.mutate({ [key]: e.target.value || null });
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
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{item.topic}</h2>
          <StatusBadge status={item.status} />
          {item.overdue && <span className="flag-chip">Overdue</span>}
        </div>
        <p>
          {cadenceLabel(item)}
          {item.last_communicated_on && ` · last done ${item.last_communicated_on}`}
          {item.next_due && ` · next due ${item.next_due}`}
        </p>
      </header>

      {SHORT_FIELDS.map((field) => textInput(field, false))}
      <div>
        <label htmlFor="communication-direction-edit">Inside or outside the organization</label>
        <select
          id="communication-direction-edit"
          value={item.direction}
          onChange={(e) => update.mutate({ direction: e.target.value as CommunicationDirection })}
        >
          {DIRECTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="communication-responsible-edit">Responsible</label>
        <select
          id="communication-responsible-edit"
          value={item.responsible_id ?? ""}
          onChange={(e) =>
            update.mutate({ responsible_id: e.target.value ? Number(e.target.value) : null })
          }
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
        <label htmlFor="communication-status-edit">Status</label>
        <select
          id="communication-status-edit"
          value={item.status}
          onChange={(e) => update.mutate({ status: e.target.value as CommunicationStatus })}
        >
          <option value="active">Active</option>
          <option value="retired">No longer done</option>
        </select>
      </div>
      {textInput({ key: "notes", label: "Notes" }, true)}
      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the communication.")}</p>
      )}

      <section>
        <h3>Schedule</h3>
        <ScheduleForm key={item.updated_at} item={item} />
      </section>

      <section>
        <h3>When it was done</h3>
        <RecordForm itemId={communicationId} />
        {item.records.length === 0 ? (
          <p>Not recorded as done yet.</p>
        ) : (
          <ul className="completion-history">
            {item.records.map((record) => (
              <li key={record.id}>
                <span>
                  {record.communicated_on}
                  {record.summary && `: ${record.summary}`}
                </span>
                <button
                  onClick={() => setOpenEvidence((open) => (open === record.id ? null : record.id))}
                >
                  {openEvidence === record.id ? "Hide documents" : "Documents"}
                </button>
                <button
                  aria-label={`Delete the record from ${record.communicated_on}`}
                  onClick={() => deleteRecord.mutate(record.id)}
                  disabled={deleteRecord.isPending}
                >
                  Delete
                </button>
                {openEvidence === record.id && (
                  <DocumentBrowser entityType="CommunicationRecord" entityId={record.id} />
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <h3>Documents</h3>
      <DocumentBrowser entityType="CommunicationPlanItem" entityId={communicationId} />

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="CommunicationPlanItem" entityId={communicationId} />

      <AuditLogViewer entityType="CommunicationPlanItem" entityId={communicationId} />

      <div className="detail-actions">
        <button onClick={handleDelete} disabled={deleteItem.isPending}>
          Delete Communication
        </button>
      </div>
    </article>
  );
}

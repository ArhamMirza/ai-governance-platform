import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { readError } from "../../../shared/api/readError";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { usePolicies } from "../../policies/hooks";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useCloseObjective,
  useDeleteMeasurement,
  useDeleteObjective,
  useObjective,
  useRecordMeasurement,
  useReopenObjective,
  useUpdateObjective,
} from "../hooks";
import { CLOSE_OPTIONS, DIRECTION_OPTIONS, formatValue, stateLabel, targetLabel } from "../labels";
import type {
  ObjectiveCloseInput,
  ObjectiveDetail as ObjectiveDetailData,
  ObjectiveUpdateInput,
  TargetDirection,
} from "../types";
import { ObjectiveAISystemLinks } from "./ObjectiveAISystemLinks";
import { ObjectiveFlags } from "./ObjectiveList";
import { ObjectiveTrendChart } from "./ObjectiveTrendChart";

type TextField =
  | "title"
  | "description"
  | "planned_actions"
  | "resources"
  | "evaluation_method"
  | "metric_name"
  | "unit";

// ISO/IEC 42001 6.2: what will be done, with what resources, and how the
// results will be evaluated.
const PLAN_FIELDS: { key: TextField; label: string }[] = [
  { key: "planned_actions", label: "What will be done" },
  { key: "resources", label: "Resources needed" },
  { key: "evaluation_method", label: "How results will be evaluated" },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function StandingSummary({ objective }: { objective: ObjectiveDetailData }) {
  const { standing } = objective;
  if (objective.status !== "active") {
    return (
      <p>
        Closed as {stateLabel(standing.state).toLowerCase()} on {objective.closed_on}
        {objective.closure_note && `: ${objective.closure_note}`}
      </p>
    );
  }
  if (objective.kind === "milestone") {
    return <p>Due by {objective.target_date}.</p>;
  }
  return (
    <p>
      {standing.latest_value === null
        ? "No reading yet"
        : `Latest ${formatValue(standing.latest_value, objective.unit)} on ${standing.latest_on}`}
      {" · "}target {targetLabel(objective.direction, objective.target_value, objective.unit)}
      {objective.target_date && ` by ${objective.target_date}`}
      {standing.next_measurement_due && ` · next reading due ${standing.next_measurement_due}`}
    </p>
  );
}

/** Interval and first-reading date are saved together -- the server
 * refuses one without the other. */
function MeasurementScheduleForm({ objective }: { objective: ObjectiveDetailData }) {
  const update = useUpdateObjective(objective.id);
  const [interval, setInterval] = useState(
    objective.measurement_interval_months?.toString() ?? "",
  );
  const [firstDue, setFirstDue] = useState(objective.first_measurement_due ?? "");
  const complete = (interval === "") === (firstDue === "");

  return (
    <div>
      <label htmlFor="objective-interval-edit">Measure every (months)</label>
      <input
        id="objective-interval-edit"
        type="number"
        min={1}
        value={interval}
        onChange={(e) => setInterval(e.target.value)}
      />
      <label htmlFor="objective-first-due-edit">First reading due</label>
      <input
        id="objective-first-due-edit"
        type="date"
        value={firstDue}
        onChange={(e) => setFirstDue(e.target.value)}
      />
      <button
        onClick={() =>
          update.mutate({
            measurement_interval_months: interval ? Number(interval) : null,
            first_measurement_due: firstDue || null,
          })
        }
        disabled={!complete || update.isPending}
      >
        Save schedule
      </button>
      {!complete && <p className="approval-note">Set both, or clear both for no schedule.</p>}
    </div>
  );
}

function RecordReadingForm({ objectiveId }: { objectiveId: number }) {
  const record = useRecordMeasurement(objectiveId);
  const [measuredOn, setMeasuredOn] = useState(todayIso());
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");

  const submit = async () => {
    await record.mutateAsync({ measured_on: measuredOn, value: Number(value), note: note || null });
    setValue("");
    setNote("");
  };

  return (
    <div className="inline-form">
      <label htmlFor="objective-reading-date">Measured on</label>
      <input
        id="objective-reading-date"
        type="date"
        max={todayIso()}
        value={measuredOn}
        onChange={(e) => setMeasuredOn(e.target.value)}
      />
      <label htmlFor="objective-reading-value">Value</label>
      <input
        id="objective-reading-value"
        type="number"
        step="any"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <label htmlFor="objective-reading-note">Note</label>
      <input id="objective-reading-note" value={note} onChange={(e) => setNote(e.target.value)} />
      <button
        onClick={submit}
        disabled={!measuredOn || value === "" || Number.isNaN(Number(value)) || record.isPending}
      >
        Record Reading
      </button>
      {record.isError && (
        <p role="alert">{readError(record.error, "Failed to record the reading.")}</p>
      )}
    </div>
  );
}

function CloseObjectiveForm({ objectiveId }: { objectiveId: number }) {
  const close = useCloseObjective(objectiveId);
  const [status, setStatus] = useState<ObjectiveCloseInput["status"]>("achieved");
  const [note, setNote] = useState("");

  return (
    <div className="inline-form">
      <label htmlFor="objective-close-status">Close as</label>
      <select
        id="objective-close-status"
        value={status}
        onChange={(e) => setStatus(e.target.value as ObjectiveCloseInput["status"])}
      >
        {CLOSE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <label htmlFor="objective-close-note">Why</label>
      <input id="objective-close-note" value={note} onChange={(e) => setNote(e.target.value)} />
      <button
        onClick={() => close.mutate({ status, closure_note: note || null })}
        disabled={close.isPending}
      >
        Close Objective
      </button>
    </div>
  );
}

export function ObjectiveDetail({ objectiveId }: { objectiveId: number }) {
  const { data: objective, isLoading, isError } = useObjective(objectiveId);
  const { data: directory } = useUserDirectory();
  const { data: policies } = usePolicies();
  const update = useUpdateObjective(objectiveId);
  const reopen = useReopenObjective(objectiveId);
  const deleteObjective = useDeleteObjective();
  const deleteMeasurement = useDeleteMeasurement();
  const navigate = useNavigate();
  const [openEvidence, setOpenEvidence] = useState<number | null>(null);

  if (isLoading) return <p>Loading objective...</p>;
  if (isError || !objective) return <p>Failed to load objective.</p>;

  const measured = objective.kind === "measured";
  const active = objective.status === "active";
  const save = (data: ObjectiveUpdateInput) => update.mutate(data);

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${objective.title}"?`)) return;
    await deleteObjective.mutateAsync(objectiveId);
    navigate("/objectives");
  };

  const textInput = ({ key, label }: { key: TextField; label: string }, multiline: boolean) => {
    const props = {
      id: `objective-${key}`,
      defaultValue: objective[key] ?? "",
      onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.target.value !== (objective[key] ?? "")) {
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

  const numberInput = (key: "target_value" | "baseline_value", label: string) => (
    <div>
      <label htmlFor={`objective-${key}`}>{label}</label>
      <input
        id={`objective-${key}`}
        type="number"
        step="any"
        defaultValue={objective[key] ?? ""}
        onBlur={(e) => {
          const next = e.target.value === "" ? null : Number(e.target.value);
          if (next !== objective[key]) save({ [key]: next });
        }}
      />
    </div>
  );

  return (
    <article key={objective.updated_at}>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{objective.title}</h2>
          <StatusBadge status={objective.standing.state} />
          <ObjectiveFlags objective={objective} />
        </div>
        <StandingSummary objective={objective} />
      </header>

      {textInput({ key: "title", label: "Objective" }, false)}
      {textInput({ key: "description", label: "Description" }, true)}
      <div>
        <label htmlFor="objective-owner-edit">Owner</label>
        <select
          id="objective-owner-edit"
          value={objective.owner_id ?? ""}
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
        <label htmlFor="objective-policy-edit">Supports policy</label>
        <select
          id="objective-policy-edit"
          value={objective.policy_id ?? ""}
          onChange={(e) => save({ policy_id: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">None</option>
          {(policies ?? []).map((policy) => (
            <option key={policy.id} value={policy.id}>
              {policy.title}
            </option>
          ))}
        </select>
        {objective.policy_id !== null && (
          <Link to={`/policies/${objective.policy_id}`}>Open policy</Link>
        )}
      </div>
      <div>
        <label htmlFor="objective-established-edit">Set on</label>
        <input
          id="objective-established-edit"
          type="date"
          value={objective.established_on}
          onChange={(e) => e.target.value && save({ established_on: e.target.value })}
        />
      </div>
      <div>
        <label htmlFor="objective-target-date-edit">Target date</label>
        <input
          id="objective-target-date-edit"
          type="date"
          value={objective.target_date ?? ""}
          onChange={(e) => save({ target_date: e.target.value || null })}
        />
      </div>
      {update.isError && (
        <p role="alert">{readError(update.error, "Failed to save the objective.")}</p>
      )}

      <section>
        <h3>Plan</h3>
        {PLAN_FIELDS.map((field) => textInput(field, true))}
      </section>

      {measured && (
        <section>
          <h3>Measurement</h3>
          {textInput({ key: "metric_name", label: "Metric" }, false)}
          <div>
            <label htmlFor="objective-direction-edit">Target</label>
            <select
              id="objective-direction-edit"
              value={objective.direction ?? "at_least"}
              onChange={(e) => save({ direction: e.target.value as TargetDirection })}
            >
              {DIRECTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          {numberInput("target_value", "Target value")}
          {textInput({ key: "unit", label: "Unit" }, false)}
          {numberInput("baseline_value", "Baseline")}
          <MeasurementScheduleForm objective={objective} />

          {objective.direction !== null && objective.target_value !== null && (
            <ObjectiveTrendChart
              measurements={objective.measurements}
              direction={objective.direction}
              target={objective.target_value}
              baseline={objective.baseline_value}
              unit={objective.unit}
            />
          )}
          {active ? (
            <RecordReadingForm objectiveId={objectiveId} />
          ) : (
            <p className="approval-note">This objective is closed; reopen it to record readings.</p>
          )}
          {objective.measurements.length === 0 ? (
            <p>No readings recorded yet.</p>
          ) : (
            <ul className="completion-history">
              {objective.measurements.map((measurement) => (
                <li key={measurement.id}>
                  <span>
                    {measurement.measured_on}: {formatValue(measurement.value, objective.unit)}
                    {measurement.note && ` — ${measurement.note}`}
                  </span>
                  <button
                    onClick={() =>
                      setOpenEvidence((open) => (open === measurement.id ? null : measurement.id))
                    }
                  >
                    {openEvidence === measurement.id ? "Hide documents" : "Documents"}
                  </button>
                  <button
                    aria-label={`Delete the reading from ${measurement.measured_on}`}
                    onClick={() => deleteMeasurement.mutate(measurement.id)}
                    disabled={deleteMeasurement.isPending}
                  >
                    Delete
                  </button>
                  {openEvidence === measurement.id && (
                    <DocumentBrowser entityType="ObjectiveMeasurement" entityId={measurement.id} />
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <ObjectiveAISystemLinks objective={objective} />

      <section>
        <h3>Outcome</h3>
        {active ? (
          <CloseObjectiveForm objectiveId={objectiveId} />
        ) : (
          <button onClick={() => reopen.mutate()} disabled={reopen.isPending}>
            Reopen Objective
          </button>
        )}
      </section>

      <h3>Documents</h3>
      <DocumentBrowser entityType="AIObjective" entityId={objectiveId} />

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="AIObjective" entityId={objectiveId} />

      <AuditLogViewer entityType="AIObjective" entityId={objectiveId} />

      <div className="detail-actions">
        {objective.measurements.length > 0 ? (
          <p className="approval-note">
            Objectives with readings are kept as monitoring evidence; close it as withdrawn instead
            of deleting it.
          </p>
        ) : (
          <button onClick={handleDelete} disabled={deleteObjective.isPending}>
            Delete Objective
          </button>
        )}
      </div>
    </article>
  );
}

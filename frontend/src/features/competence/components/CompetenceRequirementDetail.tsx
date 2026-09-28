import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/httpClient";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { useGovernanceRoles } from "../../governance-roles/hooks";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useCompetenceRequirement,
  useDeleteCompetenceRequirement,
  useDeleteCompletion,
  useRecordCompletion,
  useUpdateCompetenceRequirement,
} from "../hooks";
import { refreshLabel } from "../labels";
import type { PersonCompetence } from "../types";

interface CompetenceRequirementDetailProps {
  requirementId: number;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function RecordCompletionForm({
  requirementId,
  userId,
  label,
}: {
  requirementId: number;
  userId: number;
  label: string;
}) {
  const recordCompletion = useRecordCompletion(requirementId);
  const [completedOn, setCompletedOn] = useState(todayIso());

  return (
    <span className="inline-form">
      <input
        type="date"
        aria-label={`Completed on for ${label}`}
        value={completedOn}
        max={todayIso()}
        onChange={(e) => setCompletedOn(e.target.value)}
      />
      <button
        onClick={() => recordCompletion.mutate({ user_id: userId, completed_on: completedOn })}
        disabled={!completedOn || recordCompletion.isPending}
      >
        Record completion
      </button>
      {recordCompletion.isError && (
        <span role="alert">
          {recordCompletion.error instanceof ApiError
            ? recordCompletion.error.message
            : "Failed to record completion."}
        </span>
      )}
    </span>
  );
}

export function CompetenceRequirementDetail({ requirementId }: CompetenceRequirementDetailProps) {
  const { data: requirement, isLoading, isError } = useCompetenceRequirement(requirementId);
  const { data: roles } = useGovernanceRoles();
  const { data: directory } = useUserDirectory();
  const updateRequirement = useUpdateCompetenceRequirement(requirementId);
  const deleteRequirement = useDeleteCompetenceRequirement();
  const deleteCompletion = useDeleteCompletion();
  const navigate = useNavigate();
  const [openCertificate, setOpenCertificate] = useState<number | null>(null);

  if (isLoading) return <p>Loading competence requirement...</p>;
  if (isError || !requirement) return <p>Failed to load competence requirement.</p>;

  const nameFor = (userId: number) => {
    const user = directory?.find((candidate) => candidate.id === userId);
    return user ? formatUserOption(user) : `User #${userId}`;
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${requirement.title}" and all its completion records?`)) return;
    await deleteRequirement.mutateAsync(requirementId);
    navigate("/competence");
  };

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{requirement.title}</h2>
          {requirement.gap_count > 0 && (
            <span className="flag-chip">{requirement.gap_count} outstanding</span>
          )}
        </div>
        <p>
          {requirement.current_count} of {requirement.required_count} people competent ·{" "}
          {refreshLabel(requirement.refresh_interval_months)}
        </p>
      </header>

      <div>
        <label htmlFor="competence-description-edit">What it covers</label>
        <textarea
          id="competence-description-edit"
          defaultValue={requirement.description ?? ""}
          onBlur={(e) => {
            if (e.target.value !== (requirement.description ?? "")) {
              updateRequirement.mutate({ description: e.target.value || null });
            }
          }}
        />
      </div>

      <div>
        <label htmlFor="competence-applies-to-edit">Applies to</label>
        <select
          id="competence-applies-to-edit"
          value={requirement.governance_role_id ?? ""}
          onChange={(e) =>
            updateRequirement.mutate({
              governance_role_id: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">Everyone</option>
          {(roles ?? []).map((role) => (
            <option key={role.id} value={role.id}>
              {role.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="competence-refresh-edit">Refresh every (months, blank for once)</label>
        <input
          id="competence-refresh-edit"
          type="number"
          min={1}
          defaultValue={requirement.refresh_interval_months ?? ""}
          onBlur={(e) => {
            const value = e.target.value ? Number(e.target.value) : null;
            if (value !== requirement.refresh_interval_months && (value === null || value >= 1)) {
              updateRequirement.mutate({ refresh_interval_months: value });
            }
          }}
        />
      </div>

      <section>
        <h3>People</h3>
        {requirement.people.length === 0 ? (
          <p>
            Nobody is required yet -- no one holds this role, or there are no active users.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Status</th>
                <th>Last completed</th>
                <th>Next due</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {requirement.people.map((person: PersonCompetence) => (
                <tr
                  key={person.user_id}
                  className={person.status !== "current" ? "row-flagged" : undefined}
                >
                  <td>{nameFor(person.user_id)}</td>
                  <td>
                    <StatusBadge status={person.status} />
                  </td>
                  <td data-type="date">{person.last_completed_on ?? "—"}</td>
                  <td data-type="date">{person.next_due ?? "—"}</td>
                  <td>
                    <RecordCompletionForm
                      requirementId={requirementId}
                      userId={person.user_id}
                      label={nameFor(person.user_id)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h3>Completion History</h3>
        {requirement.records.length === 0 ? (
          <p>No completions recorded yet.</p>
        ) : (
          <ul className="completion-history">
            {requirement.records.map((record) => (
              <li key={record.id}>
                <span>
                  {nameFor(record.user_id)} completed on {record.completed_on}
                  {record.notes && ` -- ${record.notes}`}
                </span>
                <button
                  onClick={() =>
                    setOpenCertificate((open) => (open === record.id ? null : record.id))
                  }
                >
                  {openCertificate === record.id ? "Hide certificate" : "Certificate"}
                </button>
                <button
                  onClick={() => deleteCompletion.mutate(record.id)}
                  disabled={deleteCompletion.isPending}
                >
                  Delete
                </button>
                {openCertificate === record.id && (
                  <DocumentBrowser entityType="CompetenceRecord" entityId={record.id} />
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="CompetenceRequirement" entityId={requirementId} />

      <AuditLogViewer entityType="CompetenceRequirement" entityId={requirementId} />

      <div className="detail-actions">
        <button onClick={handleDelete} disabled={deleteRequirement.isPending}>
          Delete Requirement
        </button>
      </div>
    </article>
  );
}

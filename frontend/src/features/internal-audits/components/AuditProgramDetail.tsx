import { useState } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { useAuditProgram, useCreateInternalAudit, useInternalAudits, useUpdateAuditProgram } from "../hooks";

interface AuditProgramDetailProps {
  programId: number;
}

export function AuditProgramDetail({ programId }: AuditProgramDetailProps) {
  const { data: program, isLoading, isError } = useAuditProgram(programId);
  const { data: audits } = useInternalAudits(programId);
  const updateProgram = useUpdateAuditProgram(programId);
  const createAudit = useCreateInternalAudit(programId);
  const [newAuditTitle, setNewAuditTitle] = useState("");
  const [newAuditDate, setNewAuditDate] = useState("");

  if (isLoading) return <p>Loading audit program...</p>;
  if (isError || !program) return <p>Failed to load audit program.</p>;

  const handleAddAudit = async () => {
    if (!newAuditTitle.trim() || !newAuditDate) return;
    await createAudit.mutateAsync({ title: newAuditTitle, planned_date: newAuditDate });
    setNewAuditTitle("");
    setNewAuditDate("");
  };

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{program.title}</h2>
          <StatusBadge status={program.status} />
          {program.overdue && <span className="flag-chip">Overdue</span>}
        </div>
        {program.description && <p className="record-lede">{program.description}</p>}
      </header>

      <div>
        <label htmlFor="audit-program-schedule">Schedule</label>
        <p id="audit-program-schedule">
          {program.schedule_type === "interval"
            ? `Every ${program.interval_months} month(s), next due ${program.next_due_date ?? "—"}`
            : "Ad hoc"}
        </p>
      </div>

      <div className="detail-actions">
        {program.status === "active" ? (
          <button
            onClick={() => updateProgram.mutate({ status: "archived" })}
            disabled={updateProgram.isPending}
          >
            Archive Program
          </button>
        ) : (
          <button
            onClick={() => updateProgram.mutate({ status: "active" })}
            disabled={updateProgram.isPending}
          >
            Reactivate Program
          </button>
        )}
      </div>

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="AuditProgram" entityId={programId} />

      <h3>Audits</h3>
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Planned date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(audits ?? []).map((audit) => (
            <tr key={audit.id} className={audit.overdue ? "row-flagged" : undefined}>
              <td>
                <Link to={`/audit-programs/${programId}/audits/${audit.id}`}>{audit.title}</Link>
              </td>
              <td data-type="date">
                {audit.planned_date}
                {audit.overdue && <span className="flag-chip">Overdue</span>}
              </td>
              <td>
                <StatusBadge status={audit.status} />
              </td>
            </tr>
          ))}
          <tr>
            <td>
              <input
                aria-label="New audit title"
                value={newAuditTitle}
                onChange={(e) => setNewAuditTitle(e.target.value)}
              />
            </td>
            <td>
              <input
                aria-label="New audit planned date"
                type="date"
                value={newAuditDate}
                onChange={(e) => setNewAuditDate(e.target.value)}
              />
            </td>
            <td>
              <button onClick={handleAddAudit} disabled={createAudit.isPending}>
                New Audit
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <AuditLogViewer entityType="AuditProgram" entityId={programId} />
    </article>
  );
}

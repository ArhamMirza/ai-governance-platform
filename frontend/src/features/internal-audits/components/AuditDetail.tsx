import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { SourceImprovements } from "../../improvements/components/SourceImprovements";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useAuditFindings,
  useCompleteInternalAudit,
  useCreateAuditFinding,
  useInternalAudit,
  useUpdateInternalAudit,
} from "../hooks";
import type { AuditFindingType } from "../types";

interface AuditDetailProps {
  programId: number;
  auditId: number;
}

const EDITABLE_STATUSES = new Set(["planned", "in_progress"]);

export function AuditDetail({ programId, auditId }: AuditDetailProps) {
  const { data: audit, isLoading, isError } = useInternalAudit(programId, auditId);
  const { data: findings } = useAuditFindings(programId, auditId);
  const { data: directory } = useUserDirectory();
  const updateAudit = useUpdateInternalAudit(programId, auditId);
  const completeAudit = useCompleteInternalAudit(programId, auditId);
  const createFinding = useCreateAuditFinding(programId, auditId);
  const navigate = useNavigate();

  const [findingDescription, setFindingDescription] = useState("");
  const [findingType, setFindingType] = useState<AuditFindingType>("observation");

  if (isLoading) return <p>Loading audit...</p>;
  if (isError || !audit) return <p>Failed to load audit.</p>;

  const auditor = directory?.find((user) => user.id === audit.auditor_id);
  const editable = EDITABLE_STATUSES.has(audit.status);

  const handleAddFinding = async () => {
    if (!findingDescription.trim()) return;
    await createFinding.mutateAsync({ description: findingDescription, finding_type: findingType });
    setFindingDescription("");
    setFindingType("observation");
  };

  const raiseCorrectiveAction = (findingId: number, description: string) => {
    navigate("/corrective-actions", {
      state: {
        sourceType: "AuditFinding",
        sourceId: findingId,
        nonconformityDescription: description,
      },
    });
  };

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{audit.title}</h2>
          <StatusBadge status={audit.status} />
          {audit.overdue && <span className="flag-chip">Overdue</span>}
        </div>
      </header>

      <div>
        <label htmlFor="audit-auditor-edit">Auditor</label>
        {editable ? (
          <select
            id="audit-auditor-edit"
            value={audit.auditor_id ?? ""}
            onChange={(e) =>
              updateAudit.mutate({ auditor_id: e.target.value ? Number(e.target.value) : null })
            }
          >
            <option value="">Unassigned</option>
            {(directory ?? []).map((user) => (
              <option key={user.id} value={user.id}>
                {formatUserOption(user)}
              </option>
            ))}
          </select>
        ) : (
          <p>{auditor ? formatUserOption(auditor) : "Unassigned"}</p>
        )}
      </div>

      <div>
        <h3>Scope</h3>
        {editable ? (
          <textarea
            defaultValue={audit.scope ?? ""}
            onBlur={(e) => updateAudit.mutate({ scope: e.target.value })}
          />
        ) : (
          <p>{audit.scope || "Not recorded."}</p>
        )}
      </div>

      {audit.status === "completed" && (
        <div>
          <h3>Conclusion</h3>
          <p>{audit.conclusion || "Not recorded."}</p>
          <p>Conducted {audit.conducted_date}</p>
        </div>
      )}

      <div className="detail-actions">
        {editable && (
          <button onClick={() => completeAudit.mutate({})} disabled={completeAudit.isPending}>
            Complete Audit
          </button>
        )}
      </div>

      <h3>Evidence</h3>
      <DocumentBrowser entityType="InternalAudit" entityId={auditId} />

      <h3>Findings</h3>
      <table>
        <thead>
          <tr>
            <th>Description</th>
            <th>Type</th>
            <th>Corrective action</th>
            <th>Improvement</th>
          </tr>
        </thead>
        <tbody>
          {(findings ?? []).map((finding) => (
            <tr key={finding.id}>
              <td>{finding.description}</td>
              <td>{finding.finding_type === "nonconformity" ? "Nonconformity" : "Observation"}</td>
              <td>
                {finding.corrective_action_ids.length > 0 ? (
                  finding.corrective_action_ids.map((id) => (
                    <Link key={id} to={`/corrective-actions/${id}`}>
                      View corrective action
                    </Link>
                  ))
                ) : (
                  <button onClick={() => raiseCorrectiveAction(finding.id, finding.description)}>
                    Raise Corrective Action
                  </button>
                )}
              </td>
              <td>
                {/* An observation is an opportunity to improve (10.1); a
                    nonconformity goes to a corrective action (10.2). */}
                {finding.finding_type === "observation" && (
                  <SourceImprovements
                    from={{
                      sourceType: "AuditFinding",
                      sourceId: finding.id,
                      label: `a finding in ${audit.title}`,
                      description: finding.description,
                    }}
                  />
                )}
              </td>
            </tr>
          ))}
          <tr>
            <td>
              <textarea
                aria-label="New finding description"
                value={findingDescription}
                onChange={(e) => setFindingDescription(e.target.value)}
              />
            </td>
            <td>
              <select
                aria-label="New finding type"
                value={findingType}
                onChange={(e) => setFindingType(e.target.value as AuditFindingType)}
              >
                <option value="observation">Observation</option>
                <option value="nonconformity">Nonconformity</option>
              </select>
            </td>
            <td>
              <button onClick={handleAddFinding} disabled={createFinding.isPending}>
                Add Finding
              </button>
            </td>
            <td />
          </tr>
        </tbody>
      </table>
    </article>
  );
}

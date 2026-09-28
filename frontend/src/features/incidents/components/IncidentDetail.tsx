import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../../../shared/api/httpClient";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useIncident, useUpdateIncident } from "../hooks";
import { SERIOUS_CATEGORY_OPTIONS, SEVERITY_OPTIONS, aiSystemName } from "../labels";
import type { IncidentSeverity, IncidentStatus, SeriousIncidentCategory } from "../types";

interface IncidentDetailProps {
  incidentId: number;
}

type NarrativeField = "description" | "impact_description" | "immediate_actions" | "root_cause";

const NARRATIVE_FIELDS: { key: NarrativeField; label: string }[] = [
  { key: "description", label: "What happened" },
  { key: "impact_description", label: "Who or what was affected" },
  { key: "immediate_actions", label: "Immediate actions taken" },
  { key: "root_cause", label: "Root cause" },
];

const STATUS_OPTIONS: { value: IncidentStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "investigating", label: "Investigating" },
  { value: "resolved", label: "Resolved" },
];

export function IncidentDetail({ incidentId }: IncidentDetailProps) {
  const { data: incident, isLoading, isError } = useIncident(incidentId);
  const { data: inventory } = useAISystemInventoryRows();
  const { data: directory } = useUserDirectory();
  const updateIncident = useUpdateIncident(incidentId);
  const navigate = useNavigate();

  if (isLoading) return <p>Loading incident...</p>;
  if (isError || !incident) return <p>Failed to load incident.</p>;

  const raiseCorrectiveAction = () => {
    navigate("/corrective-actions", {
      state: {
        sourceType: "AIIncident",
        sourceId: incident.id,
        nonconformityDescription: incident.description,
      },
    });
  };

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{incident.title}</h2>
          <StatusBadge status={incident.status} />
          {incident.is_serious && <span className="flag-chip">Serious</span>}
          {incident.reporting_overdue && <span className="flag-chip">Report overdue</span>}
        </div>
      </header>

      <div>
        <label htmlFor="incident-status-edit">Status</label>
        <select
          id="incident-status-edit"
          value={incident.status}
          onChange={(e) => updateIncident.mutate({ status: e.target.value as IncidentStatus })}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {updateIncident.isError && (
        <p role="alert">
          {updateIncident.error instanceof ApiError
            ? updateIncident.error.message
            : "Failed to save the incident."}
        </p>
      )}

      <div>
        <label htmlFor="incident-severity-edit">Severity</label>
        <select
          id="incident-severity-edit"
          value={incident.severity}
          onChange={(e) =>
            updateIncident.mutate({ severity: e.target.value as IncidentSeverity })
          }
        >
          {SEVERITY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="incident-ai-system-edit">AI system</label>
        <select
          id="incident-ai-system-edit"
          value={incident.ai_system_row_id ?? ""}
          onChange={(e) =>
            updateIncident.mutate({
              ai_system_row_id: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">Not about one system</option>
          {(inventory?.rows ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {aiSystemName(row, row.id)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="incident-owner-edit">Handled by</label>
        <select
          id="incident-owner-edit"
          value={incident.owner_id ?? ""}
          onChange={(e) =>
            updateIncident.mutate({ owner_id: e.target.value ? Number(e.target.value) : null })
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
        <label htmlFor="incident-detected-on-edit">Detected on</label>
        <input
          id="incident-detected-on-edit"
          type="date"
          value={incident.detected_on}
          onChange={(e) => e.target.value && updateIncident.mutate({ detected_on: e.target.value })}
        />
      </div>

      <div>
        <label htmlFor="incident-occurred-on-edit">Occurred on</label>
        <input
          id="incident-occurred-on-edit"
          type="date"
          value={incident.occurred_on ?? ""}
          onChange={(e) => updateIncident.mutate({ occurred_on: e.target.value || null })}
        />
      </div>

      {NARRATIVE_FIELDS.map(({ key, label }) => (
        <div key={key}>
          <label htmlFor={`incident-${key}`}>{label}</label>
          <textarea
            id={`incident-${key}`}
            defaultValue={incident[key] ?? ""}
            onBlur={(e) => {
              if (e.target.value !== (incident[key] ?? "")) {
                updateIncident.mutate({ [key]: e.target.value });
              }
            }}
          />
        </div>
      ))}

      <section>
        <h3>Serious incident (EU AI Act Art. 73)</h3>
        <label>
          <input
            type="checkbox"
            checked={incident.is_serious}
            onChange={(e) =>
              updateIncident.mutate(
                e.target.checked
                  ? { is_serious: true, serious_category: "other" }
                  : { is_serious: false },
              )
            }
          />
          This is a serious incident that must be reported to the authority
        </label>

        {incident.is_serious && (
          <>
            <div>
              <label htmlFor="incident-serious-category">Kind of serious incident</label>
              <select
                id="incident-serious-category"
                value={incident.serious_category ?? "other"}
                onChange={(e) =>
                  updateIncident.mutate({
                    serious_category: e.target.value as SeriousIncidentCategory,
                  })
                }
              >
                {SERIOUS_CATEGORY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <p>
              Report to the market surveillance authority by{" "}
              <strong>{incident.reporting_deadline}</strong>.
            </p>
            <div>
              <label htmlFor="incident-authority-notified-on">Authority notified on</label>
              <input
                id="incident-authority-notified-on"
                type="date"
                value={incident.authority_notified_on ?? ""}
                onChange={(e) =>
                  updateIncident.mutate({ authority_notified_on: e.target.value || null })
                }
              />
            </div>
            <div>
              <label htmlFor="incident-authority-reference">Authority reference</label>
              <input
                id="incident-authority-reference"
                defaultValue={incident.authority_reference ?? ""}
                onBlur={(e) => {
                  if (e.target.value !== (incident.authority_reference ?? "")) {
                    updateIncident.mutate({ authority_reference: e.target.value || null });
                  }
                }}
              />
            </div>
          </>
        )}
      </section>

      <section>
        <h3>Corrective Actions</h3>
        {incident.corrective_action_ids.length > 0 ? (
          <ul>
            {incident.corrective_action_ids.map((id) => (
              <li key={id}>
                <Link to={`/corrective-actions/${id}`}>Corrective action #{id}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>No corrective action raised yet.</p>
        )}
        <button onClick={raiseCorrectiveAction}>Raise Corrective Action</button>
      </section>

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="AIIncident" entityId={incidentId} />

      <h3>Evidence</h3>
      <DocumentBrowser entityType="AIIncident" entityId={incidentId} />

      <AuditLogViewer entityType="AIIncident" entityId={incidentId} />
    </article>
  );
}

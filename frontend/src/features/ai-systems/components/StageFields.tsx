import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useApproveDeployment,
  useApproveRetirement,
  useRequestDeploymentApproval,
  useRequestRetirementApproval,
  useSetDeploymentRecord,
  useSetMonitoring,
  useSetOwner,
  useSetRetirement,
} from "../hooks";
import type { AISystemLifecycle } from "../types";

interface StageFieldsProps {
  rowId: number;
  lifecycle: AISystemLifecycle;
}

/** Who is accountable for this system across its whole lifecycle. Shown
 * unconditionally, unlike the stage-gated fields below -- ownership isn't
 * a gate requirement, just an always-visible accountability record. */
export function OwnerField({ rowId, lifecycle }: StageFieldsProps) {
  const save = useSetOwner(rowId);
  const { data: directory } = useUserDirectory();
  const [ownerId, setOwnerId] = useState(
    lifecycle.owner_id !== null ? String(lifecycle.owner_id) : "",
  );

  const handleChange = (value: string) => {
    setOwnerId(value);
    save.mutate({ owner_id: value ? Number(value) : null });
  };

  return (
    <div className="stage-fields">
      <label htmlFor="ai-system-owner">AI System Owner</label>
      <select
        id="ai-system-owner"
        value={ownerId}
        onChange={(e) => handleChange(e.target.value)}
      >
        <option value="">Unassigned</option>
        {(directory ?? []).map((user) => (
          <option key={user.id} value={user.id}>
            {formatUserOption(user)}
          </option>
        ))}
      </select>
    </div>
  );
}

/** The structured facts the Deployment gate checks. Also reachable over the
 * API, so a CI/CD job can stamp the release it just shipped. */
export function DeploymentRecordFields({ rowId, lifecycle }: StageFieldsProps) {
  const save = useSetDeploymentRecord(rowId);
  const requestApproval = useRequestDeploymentApproval(rowId);
  const approve = useApproveDeployment(rowId);
  const { canApprove, reason: approvalReason } = useCanApprove(
    "AISystemDeploymentApproval",
    rowId,
  );
  const [environment, setEnvironment] = useState(lifecycle.deployment_environment ?? "");
  const [version, setVersion] = useState(lifecycle.deployment_version ?? "");
  const [deployedAt, setDeployedAt] = useState(lifecycle.deployed_at ?? "");
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>, fallback: string) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(readError(err, fallback));
    }
  };

  return (
    <section className="stage-fields">
      <h4>Deployment record</h4>
      {error && <p role="alert">{error}</p>}

      <div className="stage-field-row">
        <div>
          <label htmlFor="deployment-environment">Environment</label>
          <input
            id="deployment-environment"
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="deployment-version">Version</label>
          <input
            id="deployment-version"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="deployed-at">Deployment date</label>
          <input
            id="deployed-at"
            type="date"
            value={deployedAt}
            onChange={(e) => setDeployedAt(e.target.value)}
          />
        </div>
      </div>

      <button
        onClick={() =>
          run(
            () =>
              save.mutateAsync({
                deployment_environment: environment || null,
                deployment_version: version || null,
                deployed_at: deployedAt || null,
              }),
            "Failed to save the deployment record",
          )
        }
        disabled={save.isPending}
      >
        {save.isPending ? "Saving..." : "Save deployment record"}
      </button>

      <h4>Release approval</h4>
      {lifecycle.deployment_approved_by !== null ? (
        <p className="approval-note">
          Approved{lifecycle.deployment_approved_at
            ? ` on ${new Date(lifecycle.deployment_approved_at).toLocaleDateString()}`
            : ""}
          .
        </p>
      ) : (
        <div className="stage-gate-actions">
          <button
            onClick={() =>
              run(() => requestApproval.mutateAsync(), "Failed to request approval")
            }
            disabled={requestApproval.isPending}
          >
            Request approval
          </button>
          {canApprove ? (
            <button
              onClick={() =>
                run(() => approve.mutateAsync(), "Failed to approve the release")
              }
              disabled={approve.isPending}
            >
              Approve release
            </button>
          ) : (
            <p className="approval-note">{approvalReason}</p>
          )}
        </div>
      )}
      <p className="gate-detail">
        The release must be approved by the Chief AI Governance Officer, and not by
        whoever requested it.
      </p>
    </section>
  );
}

/** The structured facts the Operation & Monitoring gate checks. */
export function MonitoringFields({ rowId, lifecycle }: StageFieldsProps) {
  const save = useSetMonitoring(rowId);
  const { data: directory } = useUserDirectory();
  const [ownerId, setOwnerId] = useState(
    lifecycle.monitoring_owner_id !== null ? String(lifecycle.monitoring_owner_id) : "",
  );
  const [escalation, setEscalation] = useState(lifecycle.incident_escalation_path ?? "");
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setError(null);
    try {
      await save.mutateAsync({
        monitoring_owner_id: ownerId ? Number(ownerId) : null,
        incident_escalation_path: escalation || null,
      });
    } catch (err) {
      setError(readError(err, "Failed to save monitoring details"));
    }
  };

  return (
    <section className="stage-fields">
      <h4>Monitoring</h4>
      {error && <p role="alert">{error}</p>}

      <div>
        <label htmlFor="monitoring-owner">Monitoring owner</label>
        <select
          id="monitoring-owner"
          value={ownerId}
          onChange={(e) => setOwnerId(e.target.value)}
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
        <label htmlFor="incident-escalation">Incident escalation path</label>
        <textarea
          id="incident-escalation"
          rows={2}
          placeholder="Who is contacted, and how, when this system misbehaves in production."
          value={escalation}
          onChange={(e) => setEscalation(e.target.value)}
        />
      </div>

      <button onClick={handleSave} disabled={save.isPending}>
        {save.isPending ? "Saving..." : "Save monitoring details"}
      </button>
    </section>
  );
}

/** The decision to retire, and how long the record is kept afterwards. */
export function RetirementFields({ rowId, lifecycle }: StageFieldsProps) {
  const save = useSetRetirement(rowId);
  const requestApproval = useRequestRetirementApproval(rowId);
  const approve = useApproveRetirement(rowId);
  const { canApprove, reason: approvalReason } = useCanApprove(
    "AISystemRetirementApproval",
    rowId,
  );
  const [reason, setReason] = useState(lifecycle.retirement_reason ?? "");
  const [retentionUntil, setRetentionUntil] = useState(lifecycle.retention_until ?? "");
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>, fallback: string) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(readError(err, fallback));
    }
  };

  return (
    <section className="stage-fields">
      <h4>Retirement</h4>
      {error && <p role="alert">{error}</p>}

      <div>
        <label htmlFor="retirement-reason">Why is this system being retired?</label>
        <textarea
          id="retirement-reason"
          rows={2}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          disabled={lifecycle.is_archived}
        />
      </div>

      <div>
        <label htmlFor="retention-until">Keep this record until</label>
        <input
          id="retention-until"
          type="date"
          value={retentionUntil}
          onChange={(e) => setRetentionUntil(e.target.value)}
          disabled={lifecycle.is_archived}
        />
        <p className="gate-detail">
          The archived record can't be deleted before this date.
        </p>
      </div>

      {!lifecycle.is_archived && (
        <button
          onClick={() =>
            run(
              () =>
                save.mutateAsync({
                  retirement_reason: reason || null,
                  retention_until: retentionUntil || null,
                }),
              "Failed to save the retirement details",
            )
          }
          disabled={save.isPending}
        >
          {save.isPending ? "Saving..." : "Save retirement details"}
        </button>
      )}

      <h4>Retirement approval</h4>
      {lifecycle.retirement_approved_by !== null ? (
        <p className="approval-note">
          Approved
          {lifecycle.retirement_approved_at
            ? ` on ${new Date(lifecycle.retirement_approved_at).toLocaleDateString()}`
            : ""}
          .
        </p>
      ) : (
        <div className="stage-gate-actions">
          <button
            onClick={() =>
              run(() => requestApproval.mutateAsync(), "Failed to request approval")
            }
            disabled={requestApproval.isPending}
          >
            Request approval
          </button>
          {canApprove ? (
            <button
              onClick={() =>
                run(() => approve.mutateAsync(), "Failed to approve the retirement")
              }
              disabled={approve.isPending}
            >
              Approve retirement
            </button>
          ) : (
            <p className="approval-note">{approvalReason}</p>
          )}
        </div>
      )}
      <p className="gate-detail">
        Retirement must be approved by the Chief AI Governance Officer, and not by
        whoever requested it.
      </p>
    </section>
  );
}

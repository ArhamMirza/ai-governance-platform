import { ApiError } from "../../../shared/api/httpClient";
import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useCorrectiveAction,
  useReopenCorrectiveAction,
  useSubmitForVerification,
  useUpdateCorrectiveAction,
  useVerifyAndClose,
} from "../hooks";

interface CorrectiveActionDetailProps {
  correctiveActionId: number;
}

const EDITABLE_STATUSES = new Set(["open", "in_progress"]);

export function CorrectiveActionDetail({ correctiveActionId }: CorrectiveActionDetailProps) {
  const { data: correctiveAction, isLoading, isError } = useCorrectiveAction(correctiveActionId);
  const { data: directory } = useUserDirectory();
  const updateCorrectiveAction = useUpdateCorrectiveAction(correctiveActionId);
  const submitForVerification = useSubmitForVerification(correctiveActionId);
  const verifyAndClose = useVerifyAndClose(correctiveActionId);
  const reopen = useReopenCorrectiveAction(correctiveActionId);
  const { canApprove, reason } = useCanApprove("CorrectiveAction", correctiveActionId);

  if (isLoading) return <p>Loading corrective action...</p>;
  if (isError || !correctiveAction) return <p>Failed to load corrective action.</p>;

  const assignee = directory?.find((user) => user.id === correctiveAction.assignee_id);
  const editable = EDITABLE_STATUSES.has(correctiveAction.status);

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{correctiveAction.title}</h2>
          <StatusBadge status={correctiveAction.status} />
          {correctiveAction.overdue && <span className="flag-chip">Overdue</span>}
        </div>
      </header>

      <div>
        <label htmlFor="corrective-action-assignee-edit">Assignee</label>
        {editable ? (
          <select
            id="corrective-action-assignee-edit"
            value={correctiveAction.assignee_id ?? ""}
            onChange={(e) =>
              updateCorrectiveAction.mutate({
                assignee_id: e.target.value ? Number(e.target.value) : null,
              })
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
          <p>{assignee ? formatUserOption(assignee) : "Unassigned"}</p>
        )}
      </div>

      <div>
        <label htmlFor="corrective-action-due-date-edit">Due date</label>
        {editable ? (
          <input
            id="corrective-action-due-date-edit"
            type="date"
            value={correctiveAction.due_date}
            onChange={(e) => updateCorrectiveAction.mutate({ due_date: e.target.value })}
          />
        ) : (
          <p>{correctiveAction.due_date}</p>
        )}
      </div>

      <div>
        <h3>Nonconformity</h3>
        {editable ? (
          <textarea
            defaultValue={correctiveAction.nonconformity_description}
            onBlur={(e) =>
              updateCorrectiveAction.mutate({ nonconformity_description: e.target.value })
            }
          />
        ) : (
          <p>{correctiveAction.nonconformity_description}</p>
        )}
      </div>

      <div>
        <h3>Root cause</h3>
        {editable ? (
          <textarea
            defaultValue={correctiveAction.root_cause ?? ""}
            onBlur={(e) => updateCorrectiveAction.mutate({ root_cause: e.target.value })}
          />
        ) : (
          <p>{correctiveAction.root_cause || "Not yet recorded."}</p>
        )}
      </div>

      <div>
        <h3>Corrective action taken</h3>
        {editable ? (
          <textarea
            defaultValue={correctiveAction.action_description ?? ""}
            onBlur={(e) => updateCorrectiveAction.mutate({ action_description: e.target.value })}
          />
        ) : (
          <p>{correctiveAction.action_description || "Not yet recorded."}</p>
        )}
      </div>

      <div className="detail-actions">
        {correctiveAction.status === "open" && (
          <button
            onClick={() => updateCorrectiveAction.mutate({ status: "in_progress" })}
            disabled={updateCorrectiveAction.isPending}
          >
            Start Work
          </button>
        )}
        {correctiveAction.status === "in_progress" && (
          <button
            onClick={() => submitForVerification.mutate()}
            disabled={submitForVerification.isPending}
          >
            Submit for Verification
          </button>
        )}
        {correctiveAction.status === "pending_verification" &&
          (canApprove ? (
            <button onClick={() => verifyAndClose.mutate()} disabled={verifyAndClose.isPending}>
              Verify &amp; Close
            </button>
          ) : (
            <p className="approval-note">{reason}</p>
          ))}
        {correctiveAction.status === "closed" && (
          <button onClick={() => reopen.mutate()} disabled={reopen.isPending}>
            Reopen
          </button>
        )}
      </div>
      {submitForVerification.isError && (
        <p role="alert">
          {submitForVerification.error instanceof ApiError
            ? submitForVerification.error.message
            : "Failed to submit for verification."}
        </p>
      )}

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="CorrectiveAction" entityId={correctiveActionId} />

      <h3>Evidence</h3>
      <DocumentBrowser entityType="CorrectiveAction" entityId={correctiveActionId} />

      <AuditLogViewer entityType="CorrectiveAction" entityId={correctiveActionId} />
    </article>
  );
}

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useApproveProcedure,
  useProcedure,
  useProcedureVersions,
  useSubmitForReview,
  useUpdateProcedure,
} from "../hooks";

interface ProcedureDetailProps {
  procedureId: number;
}

const HISTORY_ACTION_LABELS: Record<string, string> = {
  document_added: "Document added",
  document_removed: "Document removed",
};

export function ProcedureDetail({ procedureId }: ProcedureDetailProps) {
  const { data: procedure, isLoading, isError } = useProcedure(procedureId);
  const { data: history } = useProcedureVersions(procedureId);
  const { data: directory } = useUserDirectory();
  const submitForReview = useSubmitForReview(procedureId);
  const approve = useApproveProcedure(procedureId);
  const updateProcedure = useUpdateProcedure(procedureId);
  const { canApprove, reason } = useCanApprove("Procedure", procedureId);

  if (isLoading) return <p>Loading procedure...</p>;
  if (isError || !procedure) return <p>Failed to load procedure.</p>;

  const owner = directory?.find((user) => user.id === procedure.owner_id);

  return (
    <article>
      <h2>{procedure.title}</h2>
      <StatusBadge status={procedure.status} />
      <p>{procedure.description}</p>
      <p>Version {procedure.version}</p>

      <div>
        <label htmlFor="procedure-owner-edit">Owner</label>
        {procedure.status === "draft" ? (
          <select
            id="procedure-owner-edit"
            value={procedure.owner_id ?? ""}
            onChange={(e) =>
              updateProcedure.mutate({
                owner_id: e.target.value ? Number(e.target.value) : null,
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
          <p>{owner ? formatUserOption(owner) : "Unassigned"}</p>
        )}
      </div>

      <div className="detail-actions">
        {procedure.status === "draft" && (
          <button onClick={() => submitForReview.mutate()} disabled={submitForReview.isPending}>
            Submit for Review
          </button>
        )}
        {procedure.status === "in_review" && (
          canApprove ? (
            <button onClick={() => approve.mutate()} disabled={approve.isPending}>
              Approve
            </button>
          ) : (
            <p className="approval-note">{reason}</p>
          )
        )}
      </div>

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="Procedure" entityId={procedureId} />

      <h3>Documents</h3>
      <DocumentBrowser entityType="Procedure" entityId={procedureId} />

      <h3>Version History</h3>
      <ul>
        {history?.map((entry, index) => (
          <li key={index}>
            {HISTORY_ACTION_LABELS[entry.action] ?? entry.action}
            {typeof entry.diff?.filename === "string" ? `: ${entry.diff.filename}` : ""} —{" "}
            {new Date(entry.timestamp).toLocaleString()}
          </li>
        ))}
      </ul>

      <h3>Audit Log</h3>
      <AuditLogViewer entityType="Procedure" entityId={procedureId} />
    </article>
  );
}

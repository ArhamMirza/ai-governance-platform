import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import {
  useApproveProcedure,
  useProcedure,
  useProcedureVersions,
  useSubmitForReview,
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
  const submitForReview = useSubmitForReview(procedureId);
  const approve = useApproveProcedure(procedureId);
  const { canApprove, reason } = useCanApprove("Procedure", procedureId);

  if (isLoading) return <p>Loading procedure...</p>;
  if (isError || !procedure) return <p>Failed to load procedure.</p>;

  return (
    <article>
      <h2>{procedure.title}</h2>
      <StatusBadge status={procedure.status} />
      <p>{procedure.description}</p>
      <p>Version {procedure.version}</p>

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

import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCurrentUser } from "../../auth/hooks";
import { hasPermission } from "../../auth/permissions";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { ShareWithEmployees } from "../../staff/components/ShareWithEmployees";
import { useUserDirectory } from "../../users/hooks";
import {
  useApproveProcedure,
  useProcedure,
  useProcedureVersions,
  useRetireProcedure,
  useSetProcedureSharing,
  useSubmitForReview,
  useUpdateProcedure,
} from "../hooks";
import { ProcedureDraftPanel } from "./ProcedureDraftPanel";

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
  const retire = useRetireProcedure(procedureId);
  const updateProcedure = useUpdateProcedure(procedureId);
  const setSharing = useSetProcedureSharing(procedureId);
  const { data: me } = useCurrentUser();
  const { canApprove, reason } = useCanApprove("Procedure", procedureId);

  if (isLoading) return <p>Loading procedure...</p>;
  if (isError || !procedure) return <p>Failed to load procedure.</p>;

  const owner = directory?.find((user) => user.id === procedure.owner_id);

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>{procedure.title}</h2>
          <StatusBadge status={procedure.status} />
        </div>
        <p className="record-version">Version {procedure.version}</p>
        {procedure.description && <p className="record-lede">{procedure.description}</p>}
      </header>

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
        {procedure.status === "approved" && canApprove && (
          <button onClick={() => retire.mutate()} disabled={retire.isPending}>
            Retire Procedure
          </button>
        )}
      </div>

      <ProcedureDraftPanel procedure={procedure} />

      {hasPermission(me?.role, "edit") && (
        <ShareWithEmployees
          shared={procedure.shared_with_employees}
          approved={procedure.status === "approved"}
          pending={setSharing.isPending}
          onChange={(shared) => setSharing.mutate(shared)}
        />
      )}

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

      <AuditLogViewer entityType="Procedure" entityId={procedureId} />
    </article>
  );
}

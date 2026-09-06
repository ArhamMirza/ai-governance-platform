import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import {
  useApprovePolicy,
  usePolicy,
  usePolicyVersions,
  useSubmitForReview,
  useUpdatePolicy,
} from "../hooks";

interface PolicyDetailProps {
  policyId: number;
}

const HISTORY_ACTION_LABELS: Record<string, string> = {
  document_added: "Document added",
  document_removed: "Document removed",
};

export function PolicyDetail({ policyId }: PolicyDetailProps) {
  const { data: policy, isLoading, isError } = usePolicy(policyId);
  const { data: history } = usePolicyVersions(policyId);
  const { data: directory } = useUserDirectory();
  const submitForReview = useSubmitForReview(policyId);
  const approve = useApprovePolicy(policyId);
  const updatePolicy = useUpdatePolicy(policyId);
  const { canApprove, reason } = useCanApprove("Policy", policyId);

  if (isLoading) return <p>Loading policy...</p>;
  if (isError || !policy) return <p>Failed to load policy.</p>;

  const owner = directory?.find((user) => user.id === policy.owner_id);

  return (
    <article>
      <h2>{policy.title}</h2>
      <StatusBadge status={policy.status} />
      <p>{policy.description}</p>
      <p>Version {policy.version}</p>

      <div>
        <label htmlFor="policy-owner-edit">Owner</label>
        {policy.status === "draft" ? (
          <select
            id="policy-owner-edit"
            value={policy.owner_id ?? ""}
            onChange={(e) =>
              updatePolicy.mutate({ owner_id: e.target.value ? Number(e.target.value) : null })
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
        {policy.status === "draft" && (
          <button onClick={() => submitForReview.mutate()} disabled={submitForReview.isPending}>
            Submit for Review
          </button>
        )}
        {policy.status === "in_review" && (
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
      <FrameworkTagPicker entityType="Policy" entityId={policyId} />

      <h3>Documents</h3>
      <DocumentBrowser entityType="Policy" entityId={policyId} />

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
      <AuditLogViewer entityType="Policy" entityId={policyId} />
    </article>
  );
}

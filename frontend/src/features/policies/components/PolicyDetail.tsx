import { StatusBadge } from "../../../shared/components/StatusBadge";
import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { useApprovePolicy, usePolicy, usePolicyVersions, useSubmitForReview } from "../hooks";

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
  const submitForReview = useSubmitForReview(policyId);
  const approve = useApprovePolicy(policyId);

  if (isLoading) return <p>Loading policy...</p>;
  if (isError || !policy) return <p>Failed to load policy.</p>;

  return (
    <article>
      <h2>{policy.title}</h2>
      <StatusBadge status={policy.status} />
      <p>{policy.description}</p>
      <p>Version {policy.version}</p>

      <div className="detail-actions">
        {policy.status === "draft" && (
          <button onClick={() => submitForReview.mutate()} disabled={submitForReview.isPending}>
            Submit for Review
          </button>
        )}
        {policy.status === "in_review" && (
          <button onClick={() => approve.mutate()} disabled={approve.isPending}>
            Approve
          </button>
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

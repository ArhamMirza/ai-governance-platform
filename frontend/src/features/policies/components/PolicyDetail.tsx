import { StatusBadge } from "../../../shared/components/StatusBadge";
import { useApprovePolicy, usePolicy, usePolicyVersions, useSubmitForReview } from "../hooks";

interface PolicyDetailProps {
  policyId: number;
}

export function PolicyDetail({ policyId }: PolicyDetailProps) {
  const { data: policy, isLoading, isError } = usePolicy(policyId);
  const { data: versions } = usePolicyVersions(policyId);
  const submitForReview = useSubmitForReview(policyId);
  const approve = useApprovePolicy(policyId);

  if (isLoading) return <p>Loading policy...</p>;
  if (isError || !policy) return <p>Failed to load policy.</p>;

  return (
    <article>
      <h2>{policy.title}</h2>
      <StatusBadge status={policy.status} />
      <p>{policy.description}</p>
      <pre>{policy.content}</pre>

      <div>
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

      <h3>Version History</h3>
      <ul>
        {versions?.map((version) => (
          <li key={version.id}>
            v{version.version_no} — {version.change_note ?? "No note"}
          </li>
        ))}
      </ul>
    </article>
  );
}

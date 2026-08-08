import { useParams } from "react-router-dom";

import { PolicyDetail } from "../features/policies/components/PolicyDetail";

export function PolicyDetailPage() {
  const { policyId } = useParams<{ policyId: string }>();
  const id = Number(policyId);

  if (!policyId || Number.isNaN(id)) return <p>Invalid policy id.</p>;

  return <PolicyDetail policyId={id} />;
}

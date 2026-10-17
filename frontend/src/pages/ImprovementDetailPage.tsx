import { useParams } from "react-router-dom";

import { ImprovementDetail } from "../features/improvements/components/ImprovementDetail";

export function ImprovementDetailPage() {
  const { improvementId } = useParams<{ improvementId: string }>();
  const id = Number(improvementId);

  if (!improvementId || Number.isNaN(id)) return <p>Invalid improvement id.</p>;

  return <ImprovementDetail improvementId={id} />;
}

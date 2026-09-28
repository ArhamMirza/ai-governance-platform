import { useParams } from "react-router-dom";

import { CompetenceRequirementDetail } from "../features/competence/components/CompetenceRequirementDetail";

export function CompetenceRequirementDetailPage() {
  const { requirementId } = useParams<{ requirementId: string }>();
  const id = Number(requirementId);

  if (!requirementId || Number.isNaN(id)) return <p>Invalid requirement id.</p>;

  return <CompetenceRequirementDetail requirementId={id} />;
}

import { useParams } from "react-router-dom";

import { ObjectiveDetail } from "../features/objectives/components/ObjectiveDetail";

export function ObjectiveDetailPage() {
  const { objectiveId } = useParams<{ objectiveId: string }>();
  const id = Number(objectiveId);

  if (!objectiveId || Number.isNaN(id)) return <p>Invalid objective id.</p>;

  return <ObjectiveDetail objectiveId={id} />;
}

import { useParams } from "react-router-dom";

import { CorrectiveActionDetail } from "../features/corrective-actions/components/CorrectiveActionDetail";

export function CorrectiveActionDetailPage() {
  const { correctiveActionId } = useParams<{ correctiveActionId: string }>();
  const id = Number(correctiveActionId);

  if (!correctiveActionId || Number.isNaN(id)) return <p>Invalid corrective action id.</p>;

  return <CorrectiveActionDetail correctiveActionId={id} />;
}

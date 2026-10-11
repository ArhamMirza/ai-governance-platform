import { useParams } from "react-router-dom";

import { ChangeDetail } from "../features/changes/components/ChangeDetail";

export function ChangeDetailPage() {
  const { changeId } = useParams<{ changeId: string }>();
  const id = Number(changeId);

  if (!changeId || Number.isNaN(id)) return <p>Invalid change id.</p>;

  return <ChangeDetail changeId={id} />;
}

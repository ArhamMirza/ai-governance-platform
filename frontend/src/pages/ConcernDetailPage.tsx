import { useParams } from "react-router-dom";

import { ConcernDetail } from "../features/concerns/components/ConcernDetail";
import { useConcernAccess } from "../features/concerns/hooks";

export function ConcernDetailPage() {
  const { concernId } = useParams<{ concernId: string }>();
  const { data: access, isLoading } = useConcernAccess();
  const id = Number(concernId);

  if (!concernId || Number.isNaN(id)) return <p>Invalid concern id.</p>;
  if (isLoading) return <p>Loading...</p>;
  if (!access?.can_handle) return <p>Only administrators can read concerns.</p>;

  return <ConcernDetail concernId={id} />;
}

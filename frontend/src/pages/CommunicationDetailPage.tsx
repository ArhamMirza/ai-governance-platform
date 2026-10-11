import { useParams } from "react-router-dom";

import { CommunicationDetail } from "../features/communications/components/CommunicationDetail";

export function CommunicationDetailPage() {
  const { communicationId } = useParams<{ communicationId: string }>();
  const id = Number(communicationId);

  if (!communicationId || Number.isNaN(id)) return <p>Invalid communication id.</p>;

  return <CommunicationDetail communicationId={id} />;
}

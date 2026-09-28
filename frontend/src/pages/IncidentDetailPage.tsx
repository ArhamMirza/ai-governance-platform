import { useParams } from "react-router-dom";

import { IncidentDetail } from "../features/incidents/components/IncidentDetail";

export function IncidentDetailPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const id = Number(incidentId);

  if (!incidentId || Number.isNaN(id)) return <p>Invalid incident id.</p>;

  return <IncidentDetail incidentId={id} />;
}

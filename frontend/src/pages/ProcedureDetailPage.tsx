import { useParams } from "react-router-dom";

import { ProcedureDetail } from "../features/procedures/components/ProcedureDetail";

export function ProcedureDetailPage() {
  const { procedureId } = useParams<{ procedureId: string }>();
  const id = Number(procedureId);

  if (!procedureId || Number.isNaN(id)) return <p>Invalid procedure id.</p>;

  return <ProcedureDetail procedureId={id} />;
}

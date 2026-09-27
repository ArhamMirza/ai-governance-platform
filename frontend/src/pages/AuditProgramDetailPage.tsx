import { useParams } from "react-router-dom";

import { AuditProgramDetail } from "../features/internal-audits/components/AuditProgramDetail";

export function AuditProgramDetailPage() {
  const { programId } = useParams<{ programId: string }>();
  const id = Number(programId);

  if (!programId || Number.isNaN(id)) return <p>Invalid audit program id.</p>;

  return <AuditProgramDetail programId={id} />;
}

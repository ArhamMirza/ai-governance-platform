import { useParams } from "react-router-dom";

import { AuditDetail } from "../features/internal-audits/components/AuditDetail";

export function AuditDetailPage() {
  const { programId, auditId } = useParams<{ programId: string; auditId: string }>();
  const programIdNumber = Number(programId);
  const auditIdNumber = Number(auditId);

  if (!programId || Number.isNaN(programIdNumber) || !auditId || Number.isNaN(auditIdNumber)) {
    return <p>Invalid audit id.</p>;
  }

  return <AuditDetail programId={programIdNumber} auditId={auditIdNumber} />;
}

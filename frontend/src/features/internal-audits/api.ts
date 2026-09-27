import { httpClient } from "../../shared/api/httpClient";
import type {
  AuditFinding,
  AuditFindingCreateInput,
  AuditFindingUpdateInput,
  AuditProgram,
  AuditProgramCreateInput,
  AuditProgramUpdateInput,
  InternalAudit,
  InternalAuditCreateInput,
  InternalAuditUpdateInput,
} from "./types";

export const auditProgramsApi = {
  list: () => httpClient.get<AuditProgram[]>("/audit-programs"),
  get: (id: number) => httpClient.get<AuditProgram>(`/audit-programs/${id}`),
  create: (data: AuditProgramCreateInput) =>
    httpClient.post<AuditProgram>("/audit-programs", data),
  update: (id: number, data: AuditProgramUpdateInput) =>
    httpClient.put<AuditProgram>(`/audit-programs/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/audit-programs/${id}`),
};

export const internalAuditsApi = {
  list: (programId: number) =>
    httpClient.get<InternalAudit[]>(`/audit-programs/${programId}/audits`),
  get: (programId: number, auditId: number) =>
    httpClient.get<InternalAudit>(`/audit-programs/${programId}/audits/${auditId}`),
  create: (programId: number, data: InternalAuditCreateInput) =>
    httpClient.post<InternalAudit>(`/audit-programs/${programId}/audits`, data),
  update: (programId: number, auditId: number, data: InternalAuditUpdateInput) =>
    httpClient.put<InternalAudit>(`/audit-programs/${programId}/audits/${auditId}`, data),
  remove: (programId: number, auditId: number) =>
    httpClient.delete<void>(`/audit-programs/${programId}/audits/${auditId}`),
  complete: (programId: number, auditId: number, conductedDate?: string, conclusion?: string) => {
    const params = new URLSearchParams();
    if (conductedDate) params.set("conducted_date", conductedDate);
    if (conclusion) params.set("conclusion", conclusion);
    const query = params.toString();
    return httpClient.post<InternalAudit>(
      `/audit-programs/${programId}/audits/${auditId}/complete${query ? `?${query}` : ""}`,
    );
  },
};

export const auditFindingsApi = {
  list: (programId: number, auditId: number) =>
    httpClient.get<AuditFinding[]>(`/audit-programs/${programId}/audits/${auditId}/findings`),
  create: (programId: number, auditId: number, data: AuditFindingCreateInput) =>
    httpClient.post<AuditFinding>(
      `/audit-programs/${programId}/audits/${auditId}/findings`,
      data,
    ),
  update: (programId: number, auditId: number, findingId: number, data: AuditFindingUpdateInput) =>
    httpClient.put<AuditFinding>(
      `/audit-programs/${programId}/audits/${auditId}/findings/${findingId}`,
      data,
    ),
  remove: (programId: number, auditId: number, findingId: number) =>
    httpClient.delete<void>(
      `/audit-programs/${programId}/audits/${auditId}/findings/${findingId}`,
    ),
};

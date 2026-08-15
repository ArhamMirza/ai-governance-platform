import { httpClient } from "../../shared/api/httpClient";
import type { AuditLogEntry } from "./types";

export const auditLogApi = {
  list: (entityType: string, entityId: number) => {
    const params = new URLSearchParams({ entity_type: entityType, entity_id: String(entityId) });
    return httpClient.get<AuditLogEntry[]>(`/audit-log?${params.toString()}`);
  },
};

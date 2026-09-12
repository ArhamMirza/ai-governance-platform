import { httpClient } from "../../shared/api/httpClient";
import type { AuditLogEntry } from "./types";

export const auditLogApi = {
  /** Omit entityId for the whole trail of an entity type, for trails recorded
   * per item under one type (a dataset's review is logged against its row id,
   * so the sheet has no single id to ask for). */
  list: (entityType: string, entityId?: number) => {
    const params = new URLSearchParams({ entity_type: entityType });
    if (entityId !== undefined) params.set("entity_id", String(entityId));
    return httpClient.get<AuditLogEntry[]>(`/audit-log?${params.toString()}`);
  },
};

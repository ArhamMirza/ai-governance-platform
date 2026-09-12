import { useQuery } from "@tanstack/react-query";

import { auditLogApi } from "./api";

export function useAuditLog(entityType: string, entityId?: number) {
  return useQuery({
    queryKey: ["audit-log", entityType, entityId],
    queryFn: () => auditLogApi.list(entityType, entityId),
    // Actions that write audit entries for this entity can originate from
    // features that have no reason to know this query key exists (e.g. a
    // sheet row edit, or a document upload elsewhere on the page) -- a short
    // poll keeps the log honest without wiring cross-feature invalidation
    // into every mutation that might touch it.
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
  });
}

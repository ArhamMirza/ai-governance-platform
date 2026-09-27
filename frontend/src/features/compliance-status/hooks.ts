import { useQuery } from "@tanstack/react-query";

import { complianceStatusApi } from "./api";

export function useComplianceStatus(framework?: string) {
  return useQuery({
    queryKey: ["compliance-status", framework ?? "all"],
    queryFn: () => complianceStatusApi.list(framework),
  });
}

export function useComplianceStatusSummary() {
  return useQuery({
    queryKey: ["compliance-status", "summary"],
    queryFn: () => complianceStatusApi.summary(),
  });
}

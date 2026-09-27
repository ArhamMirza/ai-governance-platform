import { httpClient } from "../../shared/api/httpClient";
import type { ComplianceStatusSummary, ControlComplianceStatus } from "./types";

export const complianceStatusApi = {
  list: (framework?: string) =>
    httpClient.get<ControlComplianceStatus[]>(
      framework
        ? `/compliance-status?framework=${encodeURIComponent(framework)}`
        : "/compliance-status",
    ),
  summary: () => httpClient.get<ComplianceStatusSummary>("/compliance-status/summary"),
};

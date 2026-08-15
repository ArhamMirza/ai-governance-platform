import { httpClient } from "../../shared/api/httpClient";
import type { DashboardSummary } from "./types";

export const dashboardApi = {
  getSummary: () => httpClient.get<DashboardSummary>("/dashboard/summary"),
};

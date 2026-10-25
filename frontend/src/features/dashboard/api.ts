import { httpClient } from "../../shared/api/httpClient";
import type { DashboardSummary, GettingStarted } from "./types";

export const dashboardApi = {
  getSummary: () => httpClient.get<DashboardSummary>("/dashboard/summary"),
  getGettingStarted: () => httpClient.get<GettingStarted>("/dashboard/getting-started"),
};

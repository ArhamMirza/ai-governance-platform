import { useQuery } from "@tanstack/react-query";

import { dashboardApi } from "./api";

export function useDashboardSummary() {
  return useQuery({ queryKey: ["dashboard-summary"], queryFn: dashboardApi.getSummary });
}

/** What a new installation still needs. Refetched when the page is opened, so
 * finishing a step elsewhere and coming back shows it ticked. */
export function useGettingStarted(enabled = true) {
  return useQuery({
    queryKey: ["getting-started"],
    queryFn: dashboardApi.getGettingStarted,
    enabled,
    staleTime: 0,
  });
}

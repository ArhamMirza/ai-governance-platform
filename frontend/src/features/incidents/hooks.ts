import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { incidentsApi } from "./api";
import type { IncidentCreateInput, IncidentUpdateInput } from "./types";

export const incidentsKey = ["ai-incidents"] as const;
export const incidentKey = (id: number) => ["ai-incidents", id] as const;
export const incidentAuditLogKey = (id: number) => ["audit-log", "AIIncident", id] as const;

export function useIncidents() {
  return useQuery({ queryKey: incidentsKey, queryFn: incidentsApi.list });
}

export function useIncident(id: number) {
  return useQuery({ queryKey: incidentKey(id), queryFn: () => incidentsApi.get(id) });
}

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IncidentCreateInput) => incidentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: incidentsKey });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}

/** Status and reporting changes move the dashboard's open-incident and
 * overdue-report counts as well as the record itself. */
export function useUpdateIncident(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IncidentUpdateInput) => incidentsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: incidentsKey });
      queryClient.invalidateQueries({ queryKey: incidentKey(id) });
      queryClient.invalidateQueries({ queryKey: incidentAuditLogKey(id) });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}

export function useDeleteIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => incidentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: incidentsKey });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}

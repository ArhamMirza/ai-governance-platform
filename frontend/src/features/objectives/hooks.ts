import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { objectivesApi } from "./api";
import type {
  MeasurementInput,
  ObjectiveCloseInput,
  ObjectiveInput,
  ObjectiveUpdateInput,
} from "./types";

export const objectivesKey = ["objectives"] as const;
export const objectiveKey = (id: number) => ["objectives", id] as const;

export function useObjectives() {
  return useQuery({ queryKey: objectivesKey, queryFn: () => objectivesApi.list() });
}

export function useObjectivesForAISystem(rowId: number) {
  return useQuery({
    queryKey: ["objectives", "for-ai-system", rowId],
    queryFn: () => objectivesApi.list(rowId),
  });
}

export function useObjectivesAsOf(asOf: string) {
  return useQuery({
    queryKey: ["objectives", "as-of", asOf],
    queryFn: () => objectivesApi.standingAsOf(asOf),
  });
}

export function useObjective(id: number) {
  return useQuery({ queryKey: objectiveKey(id), queryFn: () => objectivesApi.get(id) });
}

/** Any change can move an objective's standing, which shows on the list,
 * its AI systems' pages, management review, the dashboard and the
 * compliance view -- and lands in its audit log. */
function invalidateObjectives(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: objectivesKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "AIObjective"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
}

export function useCreateObjective() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ObjectiveInput) => objectivesApi.create(data),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useUpdateObjective(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ObjectiveUpdateInput) => objectivesApi.update(id, data),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useDeleteObjective() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => objectivesApi.remove(id),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useCloseObjective(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ObjectiveCloseInput) => objectivesApi.close(id, data),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useReopenObjective(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => objectivesApi.reopen(id),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useSetObjectiveAISystems(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (aiSystemRowIds: number[]) => objectivesApi.setAISystems(id, aiSystemRowIds),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useRecordMeasurement(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MeasurementInput) => objectivesApi.recordMeasurement(id, data),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

export function useDeleteMeasurement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (measurementId: number) => objectivesApi.removeMeasurement(measurementId),
    onSuccess: () => invalidateObjectives(queryClient),
  });
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { improvementsApi } from "./api";
import type {
  ImprovementInput,
  ImprovementSourceType,
  ImprovementStatusInput,
  ImprovementUpdateInput,
} from "./types";

export const improvementsKey = ["improvements"] as const;
export const improvementKey = (id: number) => ["improvements", id] as const;

export function useImprovements() {
  return useQuery({ queryKey: improvementsKey, queryFn: () => improvementsApi.list() });
}

export function useImprovementsForSource(sourceType: ImprovementSourceType, sourceId: number) {
  return useQuery({
    queryKey: ["improvements", "for-source", sourceType, sourceId],
    queryFn: () => improvementsApi.listForSource(sourceType, sourceId),
  });
}

export function useImprovementsAsOf(asOf: string) {
  return useQuery({
    queryKey: ["improvements", "as-of", asOf],
    queryFn: () => improvementsApi.standingAsOf(asOf),
  });
}

export function useImprovement(id: number) {
  return useQuery({ queryKey: improvementKey(id), queryFn: () => improvementsApi.get(id) });
}

/** Any change can move an improvement's standing, which shows on the list,
 * its source's page, management review, the dashboard and the compliance
 * view -- and lands in its audit log. */
function invalidateImprovements(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: improvementsKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "Improvement"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
}

export function useCreateImprovement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ImprovementInput) => improvementsApi.create(data),
    onSuccess: () => invalidateImprovements(queryClient),
  });
}

export function useUpdateImprovement(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ImprovementUpdateInput) => improvementsApi.update(id, data),
    onSuccess: () => invalidateImprovements(queryClient),
  });
}

export function useDeleteImprovement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => improvementsApi.remove(id),
    onSuccess: () => invalidateImprovements(queryClient),
  });
}

export function useSetImprovementStatus(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ImprovementStatusInput) => improvementsApi.setStatus(id, data),
    onSuccess: () => invalidateImprovements(queryClient),
  });
}

export function useCarryOutAsChange(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => improvementsApi.carryOutAsChange(id),
    onSuccess: () => {
      invalidateImprovements(queryClient);
      // A new planned change now exists too.
      queryClient.invalidateQueries({ queryKey: ["changes"] });
    },
  });
}

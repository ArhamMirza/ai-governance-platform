import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { competenceApi } from "./api";
import type { CompetenceRecordInput, CompetenceRequirementInput } from "./types";

export const competenceKey = ["competence"] as const;
export const requirementKey = (id: number) => ["competence", id] as const;

export function useCompetenceRequirements() {
  return useQuery({ queryKey: competenceKey, queryFn: competenceApi.list });
}

export function useCompetenceRequirement(id: number) {
  return useQuery({ queryKey: requirementKey(id), queryFn: () => competenceApi.get(id) });
}

/** Any change moves the list's counts, the dashboard's gap count and
 * "My Training", and the requirement's own audit log. */
function invalidateCompetence(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: competenceKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "CompetenceRequirement"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
}

export function useCreateCompetenceRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CompetenceRequirementInput & { title: string }) =>
      competenceApi.create(data),
    onSuccess: () => invalidateCompetence(queryClient),
  });
}

export function useUpdateCompetenceRequirement(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CompetenceRequirementInput) => competenceApi.update(id, data),
    onSuccess: () => invalidateCompetence(queryClient),
  });
}

export function useDeleteCompetenceRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => competenceApi.remove(id),
    onSuccess: () => invalidateCompetence(queryClient),
  });
}

export function useRecordCompletion(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CompetenceRecordInput) => competenceApi.recordCompletion(id, data),
    onSuccess: () => invalidateCompetence(queryClient),
  });
}

export function useDeleteCompletion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recordId: number) => competenceApi.removeRecord(recordId),
    onSuccess: () => invalidateCompetence(queryClient),
  });
}

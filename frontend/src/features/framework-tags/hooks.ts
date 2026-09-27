import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { frameworkTagsApi } from "./api";

export function frameworkTagsKey(entityType: string, entityId: number) {
  return ["framework-tags", entityType, entityId] as const;
}

export function useFrameworkTags(entityType: string, entityId: number) {
  return useQuery({
    queryKey: frameworkTagsKey(entityType, entityId),
    queryFn: () => frameworkTagsApi.get(entityType, entityId),
  });
}

/**
 * `extraInvalidateKeys` covers entities (like RiskAssessment) that embed
 * their tags in their own read response, so that view also refetches.
 */
/**
 * Controls the record's own text most resembles, via the local embedding
 * index -- never an LLM. A mutation, not a query: it's triggered by an
 * explicit "Suggest Tags" click, not fetched automatically, and its result
 * is never cached -- a person reviews it once and either keeps it or not.
 */
export function useSuggestFrameworkTags(entityType: string, entityId: number) {
  return useMutation({
    mutationFn: () => frameworkTagsApi.suggest(entityType, entityId),
  });
}

export function useSetFrameworkTags(
  entityType: string,
  entityId: number,
  extraInvalidateKeys: readonly (readonly unknown[])[] = [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (controlIds: number[]) => frameworkTagsApi.set(entityType, entityId, controlIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: frameworkTagsKey(entityType, entityId) });
      for (const key of extraInvalidateKeys) {
        queryClient.invalidateQueries({ queryKey: key });
      }
    },
  });
}

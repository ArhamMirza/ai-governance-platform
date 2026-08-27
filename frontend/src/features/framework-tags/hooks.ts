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

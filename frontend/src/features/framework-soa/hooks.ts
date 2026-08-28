import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { frameworkSoaApi } from "./api";
import type { FrameworkSoaEntryUpdate } from "./types";

const QUERY_KEY = ["framework-soa"];

export function useFrameworkSoa() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => frameworkSoaApi.list(),
  });
}

export function useUpdateFrameworkSoaEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ controlId, data }: { controlId: number; data: FrameworkSoaEntryUpdate }) =>
      frameworkSoaApi.update(controlId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

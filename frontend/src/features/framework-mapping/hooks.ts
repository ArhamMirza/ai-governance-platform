import { useQuery } from "@tanstack/react-query";

import { frameworkMappingApi } from "./api";

export function useFrameworkMapping(framework?: string) {
  return useQuery({
    queryKey: ["framework-mapping", framework ?? "all"],
    queryFn: () => frameworkMappingApi.list(framework),
  });
}

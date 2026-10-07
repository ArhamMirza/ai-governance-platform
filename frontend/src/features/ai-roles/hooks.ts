import { useQuery } from "@tanstack/react-query";

import { aiRolesApi } from "./api";

/** The fixed list of ISO/IEC 22989 roles -- it only changes with a release. */
export function useAIRoles() {
  return useQuery({
    queryKey: ["ai-roles"],
    queryFn: aiRolesApi.list,
    staleTime: Infinity,
  });
}

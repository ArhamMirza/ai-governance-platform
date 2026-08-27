import { useQuery } from "@tanstack/react-query";

import { frameworkControlsApi } from "./api";

export function useFrameworkControls() {
  return useQuery({
    queryKey: ["framework-controls"],
    queryFn: () => frameworkControlsApi.list(),
  });
}

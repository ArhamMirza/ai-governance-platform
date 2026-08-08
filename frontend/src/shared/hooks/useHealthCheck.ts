import { useQuery } from "@tanstack/react-query";

import { httpClient } from "../api/httpClient";

interface HealthStatus {
  status: string;
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => httpClient.get<HealthStatus>("/health"),
  });
}

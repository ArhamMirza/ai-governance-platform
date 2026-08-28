import { useQuery } from "@tanstack/react-query";

import { aiSystemInventoryAdapter } from "./api";

export function useAISystemInventoryRows() {
  return useQuery({ queryKey: ["ai-system-inventory"], queryFn: aiSystemInventoryAdapter.get });
}

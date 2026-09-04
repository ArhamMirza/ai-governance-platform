import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { aiSystemInventoryAdapter } from "./api";

export function useAISystemInventoryRows() {
  return useQuery({ queryKey: ["ai-system-inventory"], queryFn: aiSystemInventoryAdapter.get });
}

export function useDeleteInventoryRow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rowId: number) => aiSystemInventoryAdapter.deleteRow(rowId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-system-inventory"] });
      queryClient.invalidateQueries({ queryKey: ["ai-systems", "archive"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}

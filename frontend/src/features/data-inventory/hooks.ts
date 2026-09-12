import { useMutation, useQueryClient } from "@tanstack/react-query";

import { dataInventoryReviewApi } from "./api";

/** A review change rewrites the row's status cell, can satisfy (or un-satisfy)
 * an AI system's data gate, and moves the dashboard's pending-approval list --
 * same fan-out the AI system lifecycle hooks invalidate. */
function useInvalidateReview() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["data-inventory"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["lifecycle"] });
    queryClient.invalidateQueries({ queryKey: ["audit-log"] });
  };
}

export function useSubmitDatasetForApproval() {
  const invalidate = useInvalidateReview();
  return useMutation({
    mutationFn: (rowId: number) => dataInventoryReviewApi.submitForApproval(rowId),
    onSuccess: invalidate,
  });
}

export function useApproveDataset() {
  const invalidate = useInvalidateReview();
  return useMutation({
    mutationFn: (rowId: number) => dataInventoryReviewApi.approve(rowId),
    onSuccess: invalidate,
  });
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { suppliersApi } from "./api";
import type {
  SupplierAISystemLinkInput,
  SupplierCreateInput,
  SupplierReviewInput,
  SupplierUpdateInput,
} from "./types";

export const suppliersKey = ["suppliers"] as const;
export const supplierKey = (id: number) => ["suppliers", id] as const;
export const suppliersForAISystemKey = (rowId: number) =>
  ["suppliers", "for-ai-system", rowId] as const;

export function useSuppliers() {
  return useQuery({ queryKey: suppliersKey, queryFn: () => suppliersApi.list() });
}

export function useSuppliersForAISystem(rowId: number) {
  return useQuery({
    queryKey: suppliersForAISystemKey(rowId),
    queryFn: () => suppliersApi.list(rowId),
  });
}

export function useSupplierRiskItems(id: number) {
  return useQuery({
    queryKey: ["suppliers", id, "risk-items"],
    queryFn: () => suppliersApi.listRiskItems(id),
  });
}

export function useSupplier(id: number) {
  return useQuery({ queryKey: supplierKey(id), queryFn: () => suppliersApi.get(id) });
}

/** Any change can move the list's chips, an AI system's supplier list, the
 * dashboard's overdue/expiring counts and the supplier's audit log. */
function invalidateSuppliers(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: suppliersKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "Supplier"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
}

export function useCreateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SupplierCreateInput) => suppliersApi.create(data),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

export function useUpdateSupplier(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SupplierUpdateInput) => suppliersApi.update(id, data),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

export function useDeleteSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => suppliersApi.remove(id),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

export function useSetSupplierAISystems(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (aiSystemRowIds: number[]) => suppliersApi.setAISystems(id, aiSystemRowIds),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

export function useUpdateSupplierAISystemLink(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ aiSystemRowId, data }: { aiSystemRowId: number; data: SupplierAISystemLinkInput }) =>
      suppliersApi.updateAISystemLink(id, aiSystemRowId, data),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

export function useRecordSupplierReview(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SupplierReviewInput) => suppliersApi.recordReview(id, data),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

export function useDeleteSupplierReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reviewId: number) => suppliersApi.removeReview(reviewId),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
}

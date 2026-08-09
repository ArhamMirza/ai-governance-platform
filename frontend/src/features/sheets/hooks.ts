import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { SheetApiAdapter, SheetColumn } from "./types";

export function useSheet(queryKey: unknown[], adapter: SheetApiAdapter) {
  return useQuery({ queryKey, queryFn: adapter.get });
}

export function useSetColumns(queryKey: unknown[], adapter: SheetApiAdapter) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (columns: SheetColumn[]) => adapter.setColumns(columns),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });
}

export function useAddRow(queryKey: unknown[], adapter: SheetApiAdapter) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => adapter.addRow(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });
}

export function useUpdateRow(queryKey: unknown[], adapter: SheetApiAdapter) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ rowId, data }: { rowId: number; data: Record<string, unknown> }) =>
      adapter.updateRow(rowId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });
}

export function useDeleteRow(queryKey: unknown[], adapter: SheetApiAdapter) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rowId: number) => adapter.deleteRow(rowId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });
}

export function useUploadSheet(queryKey: unknown[], adapter: SheetApiAdapter) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => adapter.upload(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });
}

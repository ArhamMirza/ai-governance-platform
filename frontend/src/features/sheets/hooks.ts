import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import type { SheetApiAdapter, SheetColumn } from "./types";

/** Writing to a sheet can change state the owning feature also renders -- a
 * risk item edit can withdraw its assessment's approval, for instance -- so
 * callers pass the dependent query keys they want refreshed alongside the
 * sheet itself. */
function invalidate(
  queryClient: QueryClient,
  queryKey: unknown[],
  alsoInvalidate: unknown[][],
) {
  queryClient.invalidateQueries({ queryKey });
  for (const key of alsoInvalidate) {
    queryClient.invalidateQueries({ queryKey: key });
  }
}

export function useSheet(queryKey: unknown[], adapter: SheetApiAdapter) {
  return useQuery({ queryKey, queryFn: adapter.get });
}

export function useSetColumns(
  queryKey: unknown[],
  adapter: SheetApiAdapter,
  alsoInvalidate: unknown[][] = [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (columns: SheetColumn[]) => adapter.setColumns(columns),
    onSuccess: () => invalidate(queryClient, queryKey, alsoInvalidate),
  });
}

export function useAddRow(
  queryKey: unknown[],
  adapter: SheetApiAdapter,
  alsoInvalidate: unknown[][] = [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => adapter.addRow(data),
    onSuccess: () => invalidate(queryClient, queryKey, alsoInvalidate),
  });
}

export function useUpdateRow(
  queryKey: unknown[],
  adapter: SheetApiAdapter,
  alsoInvalidate: unknown[][] = [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ rowId, data }: { rowId: number; data: Record<string, unknown> }) =>
      adapter.updateRow(rowId, data),
    onSuccess: () => invalidate(queryClient, queryKey, alsoInvalidate),
  });
}

export function useDeleteRow(
  queryKey: unknown[],
  adapter: SheetApiAdapter,
  alsoInvalidate: unknown[][] = [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rowId: number) => adapter.deleteRow(rowId),
    onSuccess: () => invalidate(queryClient, queryKey, alsoInvalidate),
  });
}

export function useUploadSheet(
  queryKey: unknown[],
  adapter: SheetApiAdapter,
  alsoInvalidate: unknown[][] = [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => adapter.upload(file),
    onSuccess: () => invalidate(queryClient, queryKey, alsoInvalidate),
  });
}

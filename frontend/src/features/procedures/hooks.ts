import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { proceduresApi } from "./api";
import type { ProcedureCreateInput, ProcedureUpdateInput } from "./types";

const proceduresKey = ["procedures"] as const;
const procedureKey = (id: number) => ["procedures", id] as const;
const procedureVersionsKey = (id: number) => ["procedures", id, "versions"] as const;

export function useProcedures() {
  return useQuery({ queryKey: proceduresKey, queryFn: proceduresApi.list });
}

export function useProcedure(id: number) {
  return useQuery({ queryKey: procedureKey(id), queryFn: () => proceduresApi.get(id) });
}

export function useProcedureVersions(id: number) {
  return useQuery({
    queryKey: procedureVersionsKey(id),
    queryFn: () => proceduresApi.listVersions(id),
  });
}

export function useCreateProcedure() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProcedureCreateInput) => proceduresApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: proceduresKey }),
  });
}

export function useUpdateProcedure(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProcedureUpdateInput) => proceduresApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: proceduresKey });
      queryClient.invalidateQueries({ queryKey: procedureKey(id) });
      queryClient.invalidateQueries({ queryKey: procedureVersionsKey(id) });
    },
  });
}

export function useDeleteProcedure() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => proceduresApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: proceduresKey }),
  });
}

export function useSubmitForReview(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => proceduresApi.submitForReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: proceduresKey });
      queryClient.invalidateQueries({ queryKey: procedureKey(id) });
    },
  });
}

export function useApproveProcedure(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => proceduresApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: proceduresKey });
      queryClient.invalidateQueries({ queryKey: procedureKey(id) });
    },
  });
}

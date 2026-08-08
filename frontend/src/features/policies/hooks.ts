import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { policiesApi } from "./api";
import type { PolicyCreateInput, PolicyUpdateInput } from "./types";

const policiesKey = ["policies"] as const;
const policyKey = (id: number) => ["policies", id] as const;
const policyVersionsKey = (id: number) => ["policies", id, "versions"] as const;

export function usePolicies() {
  return useQuery({ queryKey: policiesKey, queryFn: policiesApi.list });
}

export function usePolicy(id: number) {
  return useQuery({ queryKey: policyKey(id), queryFn: () => policiesApi.get(id) });
}

export function usePolicyVersions(id: number) {
  return useQuery({
    queryKey: policyVersionsKey(id),
    queryFn: () => policiesApi.listVersions(id),
  });
}

export function useCreatePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PolicyCreateInput) => policiesApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: policiesKey }),
  });
}

export function useUpdatePolicy(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PolicyUpdateInput) => policiesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: policiesKey });
      queryClient.invalidateQueries({ queryKey: policyKey(id) });
      queryClient.invalidateQueries({ queryKey: policyVersionsKey(id) });
    },
  });
}

export function useDeletePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => policiesApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: policiesKey }),
  });
}

export function useSubmitForReview(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => policiesApi.submitForReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: policiesKey });
      queryClient.invalidateQueries({ queryKey: policyKey(id) });
    },
  });
}

export function useApprovePolicy(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => policiesApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: policiesKey });
      queryClient.invalidateQueries({ queryKey: policyKey(id) });
    },
  });
}

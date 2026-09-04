import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { aiSystemLifecycleApi, uploadStageDocument } from "./api";
import type { DeploymentRecordInput, MonitoringInput } from "./types";

export function lifecycleKey(rowId: number) {
  return ["ai-systems", rowId, "lifecycle"] as const;
}

export function useLifecycle(rowId: number) {
  return useQuery({
    queryKey: lifecycleKey(rowId),
    queryFn: () => aiSystemLifecycleApi.get(rowId),
  });
}

/** Gate requirements are computed from assessments, evidence and inventory
 * fields, so anything that changes those has to refresh the lifecycle too. */
function useInvalidateLifecycle(rowId: number) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: lifecycleKey(rowId) });
    queryClient.invalidateQueries({ queryKey: ["ai-system-inventory"] });
    queryClient.invalidateQueries({ queryKey: ["evidence"] });
    queryClient.invalidateQueries({ queryKey: ["audit-log", "AISystem", rowId] });
  };
}

export function useAdvanceStage(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: () => aiSystemLifecycleApi.advance(rowId),
    onSuccess: invalidate,
  });
}

export function useRevertStage(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: (reason: string) => aiSystemLifecycleApi.revert(rowId, reason),
    onSuccess: invalidate,
  });
}

export function useSetDeploymentRecord(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: (data: DeploymentRecordInput) =>
      aiSystemLifecycleApi.setDeploymentRecord(rowId, data),
    onSuccess: invalidate,
  });
}

export function useSetMonitoring(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: (data: MonitoringInput) => aiSystemLifecycleApi.setMonitoring(rowId, data),
    onSuccess: invalidate,
  });
}

export function useRequestDeploymentApproval(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: () => aiSystemLifecycleApi.requestDeploymentApproval(rowId),
    onSuccess: invalidate,
  });
}

export function useApproveDeployment(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: () => aiSystemLifecycleApi.approveDeployment(rowId),
    onSuccess: invalidate,
  });
}

export function useUploadStageDocument(rowId: number) {
  const invalidate = useInvalidateLifecycle(rowId);
  return useMutation({
    mutationFn: ({ documentType, file }: { documentType: string; file: File }) =>
      uploadStageDocument(rowId, documentType, file),
    onSuccess: invalidate,
  });
}

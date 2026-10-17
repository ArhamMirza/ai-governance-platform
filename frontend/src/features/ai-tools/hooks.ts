import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { aiToolsApi, staffAiToolsApi } from "./api";
import type {
  AIToolDecisionInput,
  AIToolInput,
  AIToolRequestDecisionInput,
  AIToolUpdateInput,
  StaffAIToolRequestInput,
} from "./types";

export const aiToolsKey = ["ai-tools"] as const;
export const aiToolKey = (id: number) => ["ai-tools", id] as const;
export const aiToolRequestsKey = ["ai-tool-requests"] as const;
const staffToolsKey = ["staff-ai-tools"] as const;
const staffRequestsKey = ["staff-ai-tool-requests"] as const;

export function useAITools() {
  return useQuery({ queryKey: aiToolsKey, queryFn: () => aiToolsApi.list() });
}

export function useAITool(id: number) {
  return useQuery({ queryKey: aiToolKey(id), queryFn: () => aiToolsApi.get(id) });
}

export function useAIToolRequests() {
  return useQuery({ queryKey: aiToolRequestsKey, queryFn: () => aiToolsApi.listRequests() });
}

/** A change to a tool or a request moves the register, the queue, what staff
 * are shown, the dashboard and the compliance view -- and lands in an audit log. */
function invalidateAITools(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: aiToolsKey });
  queryClient.invalidateQueries({ queryKey: aiToolRequestsKey });
  queryClient.invalidateQueries({ queryKey: staffToolsKey });
  queryClient.invalidateQueries({ queryKey: staffRequestsKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "AITool"] });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "AIToolRequest"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
}

export function useCreateAITool() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AIToolInput) => aiToolsApi.create(data),
    onSuccess: () => invalidateAITools(queryClient),
  });
}

export function useUpdateAITool(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AIToolUpdateInput) => aiToolsApi.update(id, data),
    onSuccess: () => invalidateAITools(queryClient),
  });
}

export function useDeleteAITool() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => aiToolsApi.remove(id),
    onSuccess: () => invalidateAITools(queryClient),
  });
}

export function useDecideAITool(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AIToolDecisionInput) => aiToolsApi.decide(id, data),
    onSuccess: () => invalidateAITools(queryClient),
  });
}

export function useDecideAIToolRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AIToolRequestDecisionInput }) =>
      aiToolsApi.decideRequest(id, data),
    onSuccess: () => invalidateAITools(queryClient),
  });
}

// ---------- employees ----------

export function useStaffAITools() {
  return useQuery({ queryKey: staffToolsKey, queryFn: () => staffAiToolsApi.approved() });
}

export function useRequestableAITools() {
  return useQuery({
    queryKey: ["staff-ai-tools", "requestable"],
    queryFn: () => staffAiToolsApi.requestable(),
  });
}

export function useMyAIToolRequests() {
  return useQuery({ queryKey: staffRequestsKey, queryFn: () => staffAiToolsApi.mine() });
}

export function useRequestAITool() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: StaffAIToolRequestInput) => staffAiToolsApi.request(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: staffRequestsKey }),
  });
}

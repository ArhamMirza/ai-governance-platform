import { httpClient } from "../../shared/api/httpClient";
import type {
  AITool,
  AIToolDecisionInput,
  AIToolInput,
  AIToolRequest,
  AIToolRequestDecisionInput,
  AIToolUpdateInput,
  StaffAITool,
  StaffAIToolRequest,
  StaffAIToolRequestInput,
  StaffRequestableTool,
} from "./types";

/** The governance side: the register, and the queue of requests. */
export const aiToolsApi = {
  list: () => httpClient.get<AITool[]>("/ai-tools"),
  get: (id: number) => httpClient.get<AITool>(`/ai-tools/${id}`),
  create: (data: AIToolInput) => httpClient.post<AITool>("/ai-tools", data),
  update: (id: number, data: AIToolUpdateInput) => httpClient.put<AITool>(`/ai-tools/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/ai-tools/${id}`),
  decide: (id: number, data: AIToolDecisionInput) =>
    httpClient.post<AITool>(`/ai-tools/${id}/decision`, data),
  listRequests: () => httpClient.get<AIToolRequest[]>("/ai-tools/requests"),
  decideRequest: (id: number, data: AIToolRequestDecisionInput) =>
    httpClient.post<AIToolRequest>(`/ai-tools/requests/${id}/decision`, data),
};

/** What an employee can do: see what's allowed, ask for something else. */
export const staffAiToolsApi = {
  approved: () => httpClient.get<StaffAITool[]>("/staff/ai-tools"),
  requestable: () => httpClient.get<StaffRequestableTool[]>("/staff/ai-tools/requestable"),
  request: (data: StaffAIToolRequestInput) =>
    httpClient.post<StaffAIToolRequest>("/staff/ai-tool-requests", data),
  mine: () => httpClient.get<StaffAIToolRequest[]>("/staff/ai-tool-requests/mine"),
};

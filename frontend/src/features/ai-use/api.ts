import { httpClient } from "../../shared/api/httpClient";
import type {
  AIUseSettings,
  AIUseSettingsInput,
  BuiltinDetector,
  Coverage,
  DLPRule,
  DLPRuleInput,
  DLPRuleUpdateInput,
  EnrollmentKeyIssued,
  StaffAIUseNotice,
  UsageSummary,
} from "./types";

export const dlpRulesApi = {
  list: () => httpClient.get<DLPRule[]>("/dlp-rules"),
  detectors: () => httpClient.get<BuiltinDetector[]>("/dlp-rules/detectors"),
  create: (data: DLPRuleInput) => httpClient.post<DLPRule>("/dlp-rules", data),
  update: (id: number, data: DLPRuleUpdateInput) =>
    httpClient.put<DLPRule>(`/dlp-rules/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/dlp-rules/${id}`),
};

export const aiUseApi = {
  settings: () => httpClient.get<AIUseSettings>("/ai-use/settings"),
  updateSettings: (data: AIUseSettingsInput) =>
    httpClient.put<AIUseSettings>("/ai-use/settings", data),
  rotateKey: () => httpClient.post<EnrollmentKeyIssued>("/ai-use/enrollment-key", {}),
  coverage: (days: number) => httpClient.get<Coverage>(`/ai-use/coverage?days=${days}`),
  usage: (days: number) => httpClient.get<UsageSummary>(`/ai-use/usage?days=${days}`),
};

export const staffAiUseApi = {
  notice: () => httpClient.get<StaffAIUseNotice>("/staff/ai-use-notice"),
};

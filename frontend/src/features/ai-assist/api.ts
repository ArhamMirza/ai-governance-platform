import { httpClient } from "../../shared/api/httpClient";

export type AiProvider = "anthropic" | "openai" | "gemini" | "groq" | "local";

export interface AiAssistStatus {
  available: boolean;
  provider: AiProvider | null;
  model: string | null;
  /** True when the model runs inside the deployment, so nothing leaves it. */
  is_local: boolean;
  reason: string | null;
}

export interface AiAssistSettings {
  provider: AiProvider;
  model: string;
  fast_model: string | null;
  base_url: string | null;
  daily_token_budget: number;
  /** The key itself never comes back from the server -- only whether one is set. */
  has_api_key: boolean;
  updated_at: string | null;
}

export interface AiAssistSettingsUpdate {
  provider: AiProvider;
  model: string;
  fast_model?: string | null;
  /** Omit to keep the stored key; "" to clear it. */
  api_key?: string;
  base_url?: string | null;
  daily_token_budget: number;
}

export interface DraftRequest {
  kind: string;
  impact_assessment_id: number;
  factor?: string;
}

export interface DraftResponse {
  draft: string;
  /** Text in the record that reads as an instruction aimed at a model. */
  injection_findings: string[];
}

/** What one kind of model call has cost: chat, a draft, a retry. */
export interface AiSpendFeature {
  feature: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  average_prompt_tokens: number;
  average_completion_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  /** Share of the prompt that came from a cache, 0 to 1. */
  cache_hit_rate: number;
}

export interface AiSpendReport {
  days: number;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  cache_hit_rate: number;
  by_feature: AiSpendFeature[];
  by_day: { day: string; calls: number; tokens: number }[];
}

export const aiAssistApi = {
  spend: (days: number) => httpClient.get<AiSpendReport>(`/ai-assist/spend?days=${days}`),
  status: () => httpClient.get<AiAssistStatus>("/ai-assist/status"),
  getSettings: () => httpClient.get<AiAssistSettings>("/ai-assist/settings"),
  updateSettings: (data: AiAssistSettingsUpdate) =>
    httpClient.put<AiAssistSettings>("/ai-assist/settings", data),
  draft: (data: DraftRequest) => httpClient.post<DraftResponse>("/ai-assist/draft", data),
};

import { httpClient } from "../../shared/api/httpClient";
import type { CorrectiveAction } from "../corrective-actions/types";
import type {
  Concern,
  ConcernLogInput,
  ConcernSettings,
  ConcernSettingsInput,
  ConcernStatusInput,
  ConcernSubmitInput,
  ConcernSubmitted,
  ConcernUpdateInput,
  ConcernsProcess,
  RaiseCorrectiveActionInput,
  ReporterConcern,
  StaffAISystem,
} from "./types";

/** What an employee can do: raise a concern, follow their own, look one up by
 * its tracking code. */
export const staffConcernsApi = {
  process: () => httpClient.get<ConcernsProcess>("/staff/concerns-process"),
  aiSystems: () => httpClient.get<StaffAISystem[]>("/staff/ai-systems"),
  submit: (data: ConcernSubmitInput) => httpClient.post<ConcernSubmitted>("/staff/concerns", data),
  mine: () => httpClient.get<ReporterConcern[]>("/staff/concerns/mine"),
  // A POST, not a GET: the code is a secret and a URL ends up in logs.
  lookup: (trackingCode: string) =>
    httpClient.post<ReporterConcern>("/staff/concerns/lookup", { tracking_code: trackingCode }),
};

/** The handler side: the register, triage, replies and settings. */
export const concernsApi = {
  access: () => httpClient.get<{ can_handle: boolean }>("/concerns/access"),
  list: () => httpClient.get<Concern[]>("/concerns"),
  get: (id: number) => httpClient.get<Concern>(`/concerns/${id}`),
  log: (data: ConcernLogInput) => httpClient.post<Concern>("/concerns", data),
  update: (id: number, data: ConcernUpdateInput) =>
    httpClient.put<Concern>(`/concerns/${id}`, data),
  setStatus: (id: number, data: ConcernStatusInput) =>
    httpClient.post<Concern>(`/concerns/${id}/status`, data),
  raiseIncident: (id: number) => httpClient.post<Concern>(`/concerns/${id}/raise-incident`, {}),
  listCorrectiveActions: (id: number) =>
    httpClient.get<CorrectiveAction[]>(`/concerns/${id}/corrective-actions`),
  raiseCorrectiveAction: (id: number, data: RaiseCorrectiveActionInput) =>
    httpClient.post<CorrectiveAction>(`/concerns/${id}/corrective-actions`, data),
  settings: () => httpClient.get<ConcernSettings>("/concerns/settings"),
  updateSettings: (data: ConcernSettingsInput) =>
    httpClient.put<ConcernSettings>("/concerns/settings", data),
};

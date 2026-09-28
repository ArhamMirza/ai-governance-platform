import { httpClient } from "../../shared/api/httpClient";
import type {
  ManagementReviewMeeting,
  ManagementReviewMeetingCreateInput,
  ManagementReviewMeetingUpdateInput,
  ManagementReviewSettings,
  ManagementReviewSettingsUpdateInput,
} from "./types";

export const managementReviewApi = {
  getSettings: () => httpClient.get<ManagementReviewSettings>("/management-review/settings"),
  updateSettings: (data: ManagementReviewSettingsUpdateInput) =>
    httpClient.put<ManagementReviewSettings>("/management-review/settings", data),
  listMeetings: () =>
    httpClient.get<ManagementReviewMeeting[]>("/management-review/meetings"),
  getMeeting: (id: number) =>
    httpClient.get<ManagementReviewMeeting>(`/management-review/meetings/${id}`),
  createMeeting: (data: ManagementReviewMeetingCreateInput) =>
    httpClient.post<ManagementReviewMeeting>("/management-review/meetings", data),
  updateMeeting: (id: number, data: ManagementReviewMeetingUpdateInput) =>
    httpClient.put<ManagementReviewMeeting>(`/management-review/meetings/${id}`, data),
  removeMeeting: (id: number) =>
    httpClient.delete<void>(`/management-review/meetings/${id}`),
};

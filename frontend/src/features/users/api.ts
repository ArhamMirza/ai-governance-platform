import { httpClient } from "../../shared/api/httpClient";
import type {
  CreateUserInput,
  DirectoryUser,
  ManagedUser,
  SecuritySettings,
  TemporaryPassword,
  UpdateUserInput,
  UserAccountabilities,
  UserImportPreview,
  UserImportResult,
} from "./types";

function form(file: File): FormData {
  const data = new FormData();
  data.append("file", file);
  return data;
}

export const usersApi = {
  list: () => httpClient.get<ManagedUser[]>("/users"),
  create: (data: CreateUserInput) =>
    httpClient.post<ManagedUser>("/users", data),
  update: (id: number, data: UpdateUserInput) =>
    httpClient.patch<ManagedUser>(`/users/${id}`, data),
  resetPassword: (id: number) =>
    httpClient.post<TemporaryPassword>(`/users/${id}/reset-password`),
  resetTwoStep: (id: number) =>
    httpClient.post<ManagedUser>(`/users/${id}/reset-two-step`),
  securitySettings: () =>
    httpClient.get<SecuritySettings>("/security/settings"),
  updateSecuritySettings: (requireForAdmins: boolean) =>
    httpClient.put<SecuritySettings>("/security/settings", {
      require_mfa_for_admins: requireForAdmins,
    }),
  previewImport: (file: File) =>
    httpClient.postForm<UserImportPreview>("/users/import/preview", form(file)),
  runImport: (file: File) =>
    httpClient.postForm<UserImportResult>("/users/import", form(file)),
  directory: () => httpClient.get<DirectoryUser[]>("/users/directory"),
  accountabilities: (id: number) =>
    httpClient.get<UserAccountabilities>(`/users/${id}/accountabilities`),
};

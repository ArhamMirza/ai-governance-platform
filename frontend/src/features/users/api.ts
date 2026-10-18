import { httpClient } from "../../shared/api/httpClient";
import type {
  CreateUserInput,
  DirectoryUser,
  ManagedUser,
  SecuritySettings,
  TemporaryPassword,
  UpdateUserInput,
  UserAccountabilities,
} from "./types";

export const usersApi = {
  list: () => httpClient.get<ManagedUser[]>("/users"),
  create: (data: CreateUserInput) => httpClient.post<ManagedUser>("/users", data),
  update: (id: number, data: UpdateUserInput) =>
    httpClient.patch<ManagedUser>(`/users/${id}`, data),
  resetPassword: (id: number) =>
    httpClient.post<TemporaryPassword>(`/users/${id}/reset-password`),
  resetTwoStep: (id: number) => httpClient.post<ManagedUser>(`/users/${id}/reset-two-step`),
  securitySettings: () => httpClient.get<SecuritySettings>("/security/settings"),
  updateSecuritySettings: (requireForAdmins: boolean) =>
    httpClient.put<SecuritySettings>("/security/settings", {
      require_mfa_for_admins: requireForAdmins,
    }),
  directory: () => httpClient.get<DirectoryUser[]>("/users/directory"),
  accountabilities: (id: number) =>
    httpClient.get<UserAccountabilities>(`/users/${id}/accountabilities`),
};

import { httpClient } from "../../shared/api/httpClient";
import type { AuthUser, LoginInput, RegisterInput, RegistrationStatus } from "./types";

export const authApi = {
  registrationStatus: () => httpClient.get<RegistrationStatus>("/auth/registration-status"),
  register: (data: RegisterInput) => httpClient.post<AuthUser>("/auth/register", data),
  login: (data: LoginInput) => httpClient.post<AuthUser>("/auth/login", data),
  logout: () => httpClient.post<void>("/auth/logout"),
  me: () => httpClient.get<AuthUser>("/auth/me"),
};

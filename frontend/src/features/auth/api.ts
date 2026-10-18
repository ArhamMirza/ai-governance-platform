import { httpClient } from "../../shared/api/httpClient";
import type {
  AuthUser,
  ChangePasswordInput,
  LoginInput,
  RegisterInput,
  RegistrationStatus,
  SessionsEnded,
} from "./types";

export const authApi = {
  registrationStatus: () => httpClient.get<RegistrationStatus>("/auth/registration-status"),
  register: (data: RegisterInput) => httpClient.post<AuthUser>("/auth/register", data),
  login: (data: LoginInput) => httpClient.post<AuthUser>("/auth/login", data),
  logout: () => httpClient.post<void>("/auth/logout"),
  me: () => httpClient.get<AuthUser>("/auth/me"),
  changePassword: (data: ChangePasswordInput) =>
    httpClient.post<AuthUser>("/auth/change-password", data),
  signOutEverywhere: () => httpClient.post<SessionsEnded>("/auth/sign-out-everywhere"),
};

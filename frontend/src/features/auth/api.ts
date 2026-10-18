import { httpClient } from "../../shared/api/httpClient";
import type {
  AuthUser,
  ChangePasswordInput,
  LoginInput,
  LoginResult,
  RecoveryCodes,
  RegisterInput,
  RegistrationStatus,
  SessionsEnded,
  TwoStepLoginInput,
  TwoStepProof,
  TwoStepSetup,
  TwoStepStatus,
} from "./types";

export const authApi = {
  registrationStatus: () => httpClient.get<RegistrationStatus>("/auth/registration-status"),
  register: (data: RegisterInput) => httpClient.post<AuthUser>("/auth/register", data),
  login: (data: LoginInput) => httpClient.post<LoginResult>("/auth/login", data),
  loginTwoStep: (data: TwoStepLoginInput) =>
    httpClient.post<AuthUser>("/auth/login/two-step", data),
  twoStepStatus: () => httpClient.get<TwoStepStatus>("/auth/two-step"),
  startTwoStepSetup: () => httpClient.post<TwoStepSetup>("/auth/two-step/setup"),
  confirmTwoStep: (code: string) =>
    httpClient.post<RecoveryCodes>("/auth/two-step/confirm", { code }),
  disableTwoStep: (data: TwoStepProof) => httpClient.post<void>("/auth/two-step/disable", data),
  newRecoveryCodes: (data: TwoStepProof) =>
    httpClient.post<RecoveryCodes>("/auth/two-step/recovery-codes", data),
  logout: () => httpClient.post<void>("/auth/logout"),
  me: () => httpClient.get<AuthUser>("/auth/me"),
  changePassword: (data: ChangePasswordInput) =>
    httpClient.post<AuthUser>("/auth/change-password", data),
  signOutEverywhere: () => httpClient.post<SessionsEnded>("/auth/sign-out-everywhere"),
};

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "../../shared/api/httpClient";
import { authApi } from "./api";
import {
  type AuthUser,
  type ChangePasswordInput,
  type LoginInput,
  type RegisterInput,
  type TwoStepLoginInput,
  type TwoStepProof,
  isMfaChallenge,
} from "./types";

export const currentUserKey = ["auth", "me"] as const;

export function useRegistrationStatus() {
  return useQuery({
    queryKey: ["auth", "registration-status"],
    queryFn: authApi.registrationStatus,
  });
}

/** The signed-in user, or null when there's no session. */
async function fetchCurrentUser(): Promise<AuthUser | null> {
  try {
    return await authApi.me();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** Resolves to the signed-in user, or null when there's no session.
 *
 * A 401 is an answer ("not logged in"), not a failure, so it's kept as data.
 * As an error with no data, React Query v5 puts the query back to *pending*
 * on every refetch -- window focus, a component mounting -- and AuthGate
 * swapped the sign-in form for its loading screen each time, wiping whatever
 * was being typed and sending a half-filled login. Settled as null, a
 * background refetch leaves the form alone. */
export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserKey,
    queryFn: fetchCurrentUser,
    retry: false,
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RegisterInput) => authApi.register(data),
    onSuccess: (user) => {
      queryClient.setQueryData(currentUserKey, user);
    },
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LoginInput) => authApi.login(data),
    onSuccess: (result) => {
      // An account with two-step sign-in gets only a ticket here; the session
      // (and so the signed-in user) comes from the second step.
      if (!isMfaChallenge(result)) queryClient.setQueryData(currentUserKey, result);
    },
  });
}

export function useLoginTwoStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TwoStepLoginInput) => authApi.loginTwoStep(data),
    onSuccess: (user) => {
      queryClient.setQueryData(currentUserKey, user);
    },
  });
}

const twoStepKey = ["auth", "two-step"] as const;

export function useTwoStepStatus() {
  return useQuery({ queryKey: twoStepKey, queryFn: authApi.twoStepStatus });
}

/** Asks for a new secret. Nothing is cached: it is shown once, on the screen
 * that asked for it. */
export function useStartTwoStepSetup() {
  return useMutation({ mutationFn: authApi.startTwoStepSetup });
}

/** Turns it on. Deliberately does not refresh the account on success: that
 * would flip the screen to "on" (or, for a required set-up, into the app) and
 * discard the recovery codes it is about to show. The set-up flow calls
 * useRefreshAccount once they are saved. */
export function useConfirmTwoStep() {
  return useMutation({ mutationFn: (code: string) => authApi.confirmTwoStep(code) });
}

/** Re-reads who is signed in and their two-step status. */
export function useRefreshAccount() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: currentUserKey }),
      queryClient.invalidateQueries({ queryKey: twoStepKey }),
    ]);
}

export function useDisableTwoStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TwoStepProof) => authApi.disableTwoStep(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: currentUserKey });
      void queryClient.invalidateQueries({ queryKey: twoStepKey });
    },
  });
}

export function useNewRecoveryCodes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TwoStepProof) => authApi.newRecoveryCodes(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: twoStepKey });
    },
  });
}

export function useChangePassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ChangePasswordInput) => authApi.changePassword(data),
    onSuccess: (user) => {
      // The returned user has must_change_password cleared, which is what
      // lets AuthGate swap the forced screen for the app.
      queryClient.setQueryData(currentUserKey, user);
    },
  });
}

export function useSignOutEverywhere() {
  return useMutation({ mutationFn: authApi.signOutEverywhere });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      // resetQueries (not clear()) so the mounted useCurrentUser observer
      // actually re-fetches and flips AuthGate back to the login screen --
      // clear() wipes the cache but doesn't reliably push a fresh fetch to
      // already-mounted observers, so the UI kept showing stale content
      // until a manual reload.
      queryClient.resetQueries();
    },
  });
}

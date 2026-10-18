import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "../../shared/api/httpClient";
import { authApi } from "./api";
import type { AuthUser, ChangePasswordInput, LoginInput, RegisterInput } from "./types";

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
    onSuccess: (user) => {
      queryClient.setQueryData(currentUserKey, user);
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

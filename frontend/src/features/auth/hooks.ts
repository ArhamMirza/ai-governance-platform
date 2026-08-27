import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authApi } from "./api";
import type { LoginInput, RegisterInput } from "./types";

export const currentUserKey = ["auth", "me"] as const;

export function useRegistrationStatus() {
  return useQuery({
    queryKey: ["auth", "registration-status"],
    queryFn: authApi.registrationStatus,
  });
}

/** A 401 here just means "not logged in" -- not worth retrying. */
export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserKey,
    queryFn: authApi.me,
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

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { usersApi } from "./api";
import type { CreateUserInput, UpdateUserInput } from "./types";

const usersKey = ["users"] as const;

export function useUsers(options?: { enabled?: boolean }) {
  return useQuery({ queryKey: usersKey, queryFn: usersApi.list, enabled: options?.enabled });
}

/** Any logged-in user (not just admins) can call this -- used to populate
 * pickers like risk item ownership. */
export function useUserDirectory() {
  return useQuery({ queryKey: ["users", "directory"], queryFn: usersApi.directory });
}

/** Only fetched when an id is given -- the admin is about to deactivate
 * someone and needs to know what they hold. */
export function useUserAccountabilities(userId: number | null) {
  return useQuery({
    queryKey: ["users", "accountabilities", userId],
    queryFn: () => usersApi.accountabilities(userId as number),
    enabled: userId !== null,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUserInput) => usersApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
  });
}

/** The temporary password comes back once, in the mutation result; nothing
 * is cached, so it can't reappear on a later visit. */
export function useResetPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => usersApi.resetPassword(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
  });
}

export function useResetTwoStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => usersApi.resetTwoStep(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: usersKey });
      void queryClient.invalidateQueries({ queryKey: securityKey });
    },
  });
}

const securityKey = ["security", "settings"] as const;

export function useSecuritySettings(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: securityKey,
    queryFn: usersApi.securitySettings,
    enabled: options?.enabled,
  });
}

export function useUpdateSecuritySettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requireForAdmins: boolean) => usersApi.updateSecuritySettings(requireForAdmins),
    onSuccess: (settings) => {
      queryClient.setQueryData(securityKey, settings);
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateUserInput }) =>
      usersApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
  });
}

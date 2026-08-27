import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { usersApi } from "./api";
import type { CreateUserInput, UpdateUserInput } from "./types";

const usersKey = ["users"] as const;

export function useUsers() {
  return useQuery({ queryKey: usersKey, queryFn: usersApi.list });
}

/** Any logged-in user (not just admins) can call this -- used to populate
 * pickers like risk item ownership. */
export function useUserDirectory() {
  return useQuery({ queryKey: ["users", "directory"], queryFn: usersApi.directory });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUserInput) => usersApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
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

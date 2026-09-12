import { httpClient } from "../../shared/api/httpClient";
import type {
  CreateUserInput,
  DirectoryUser,
  ManagedUser,
  UpdateUserInput,
  UserAccountabilities,
} from "./types";

export const usersApi = {
  list: () => httpClient.get<ManagedUser[]>("/users"),
  create: (data: CreateUserInput) => httpClient.post<ManagedUser>("/users", data),
  update: (id: number, data: UpdateUserInput) =>
    httpClient.patch<ManagedUser>(`/users/${id}`, data),
  directory: () => httpClient.get<DirectoryUser[]>("/users/directory"),
  accountabilities: (id: number) =>
    httpClient.get<UserAccountabilities>(`/users/${id}/accountabilities`),
};

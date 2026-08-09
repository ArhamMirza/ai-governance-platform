import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { evidenceApi, folderApi } from "./api";

const foldersKey = (entityType: string, entityId: number, parentFolderId: number | null) =>
  ["folders", entityType, entityId, parentFolderId] as const;

const evidenceKey = (entityType: string, entityId: number, folderId: number | null) =>
  ["evidence", entityType, entityId, folderId] as const;

export function useFolders(
  entityType: string,
  entityId: number,
  parentFolderId: number | null,
) {
  return useQuery({
    queryKey: foldersKey(entityType, entityId, parentFolderId),
    queryFn: () => folderApi.list(entityType, entityId, parentFolderId),
  });
}

export function useEvidenceList(
  entityType: string,
  entityId: number,
  folderId: number | null,
) {
  return useQuery({
    queryKey: evidenceKey(entityType, entityId, folderId),
    queryFn: () => evidenceApi.list(entityType, entityId, folderId),
  });
}

export function useCreateFolder(
  entityType: string,
  entityId: number,
  parentFolderId: number | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      folderApi.create(entityType, entityId, name, parentFolderId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: foldersKey(entityType, entityId, parentFolderId),
      });
    },
  });
}

export function useDeleteFolder(
  entityType: string,
  entityId: number,
  parentFolderId: number | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (folderId: number) => folderApi.remove(folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: foldersKey(entityType, entityId, parentFolderId),
      });
    },
  });
}

export function useUploadEvidence(
  entityType: string,
  entityId: number,
  folderId: number | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => evidenceApi.upload(entityType, entityId, folderId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKey(entityType, entityId, folderId) });
    },
  });
}

export function useDeleteEvidence(
  entityType: string,
  entityId: number,
  folderId: number | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: number) => evidenceApi.remove(evidenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKey(entityType, entityId, folderId) });
    },
  });
}

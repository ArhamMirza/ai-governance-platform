import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { auditFindingsApi, auditProgramsApi, internalAuditsApi } from "./api";
import type {
  AuditFindingCreateInput,
  AuditFindingUpdateInput,
  AuditProgramCreateInput,
  AuditProgramUpdateInput,
  InternalAuditCreateInput,
  InternalAuditUpdateInput,
} from "./types";

export const auditProgramsKey = ["audit-programs"] as const;
export const auditProgramKey = (id: number) => ["audit-programs", id] as const;
export const auditProgramAuditLogKey = (id: number) =>
  ["audit-log", "AuditProgram", id] as const;
export const internalAuditsKey = (programId: number) =>
  ["audit-programs", programId, "audits"] as const;
export const internalAuditKey = (programId: number, auditId: number) =>
  ["audit-programs", programId, "audits", auditId] as const;
export const internalAuditAuditLogKey = (auditId: number) =>
  ["audit-log", "InternalAudit", auditId] as const;
export const auditFindingsKey = (programId: number, auditId: number) =>
  ["audit-programs", programId, "audits", auditId, "findings"] as const;

export function useAuditPrograms() {
  return useQuery({ queryKey: auditProgramsKey, queryFn: auditProgramsApi.list });
}

export function useAuditProgram(id: number) {
  return useQuery({
    queryKey: auditProgramKey(id),
    queryFn: () => auditProgramsApi.get(id),
  });
}

export function useCreateAuditProgram() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AuditProgramCreateInput) => auditProgramsApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: auditProgramsKey }),
  });
}

function invalidateAuditProgram(queryClient: QueryClient, id: number) {
  queryClient.invalidateQueries({ queryKey: auditProgramsKey });
  queryClient.invalidateQueries({ queryKey: auditProgramKey(id) });
  queryClient.invalidateQueries({ queryKey: auditProgramAuditLogKey(id) });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
}

export function useUpdateAuditProgram(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AuditProgramUpdateInput) => auditProgramsApi.update(id, data),
    onSuccess: () => invalidateAuditProgram(queryClient, id),
  });
}

export function useDeleteAuditProgram() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => auditProgramsApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: auditProgramsKey }),
  });
}

export function useInternalAudits(programId: number) {
  return useQuery({
    queryKey: internalAuditsKey(programId),
    queryFn: () => internalAuditsApi.list(programId),
  });
}

export function useInternalAudit(programId: number, auditId: number) {
  return useQuery({
    queryKey: internalAuditKey(programId, auditId),
    queryFn: () => internalAuditsApi.get(programId, auditId),
  });
}

export function useCreateInternalAudit(programId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InternalAuditCreateInput) => internalAuditsApi.create(programId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: internalAuditsKey(programId) });
      invalidateAuditProgram(queryClient, programId);
    },
  });
}

function invalidateInternalAudit(queryClient: QueryClient, programId: number, auditId: number) {
  queryClient.invalidateQueries({ queryKey: internalAuditsKey(programId) });
  queryClient.invalidateQueries({ queryKey: internalAuditKey(programId, auditId) });
  queryClient.invalidateQueries({ queryKey: internalAuditAuditLogKey(auditId) });
  invalidateAuditProgram(queryClient, programId);
}

export function useUpdateInternalAudit(programId: number, auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InternalAuditUpdateInput) =>
      internalAuditsApi.update(programId, auditId, data),
    onSuccess: () => invalidateInternalAudit(queryClient, programId, auditId),
  });
}

export function useDeleteInternalAudit(programId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (auditId: number) => internalAuditsApi.remove(programId, auditId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: internalAuditsKey(programId) });
      invalidateAuditProgram(queryClient, programId);
    },
  });
}

export function useCompleteInternalAudit(programId: number, auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conductedDate, conclusion }: { conductedDate?: string; conclusion?: string }) =>
      internalAuditsApi.complete(programId, auditId, conductedDate, conclusion),
    onSuccess: () => invalidateInternalAudit(queryClient, programId, auditId),
  });
}

export function useAuditFindings(programId: number, auditId: number) {
  return useQuery({
    queryKey: auditFindingsKey(programId, auditId),
    queryFn: () => auditFindingsApi.list(programId, auditId),
  });
}

export function useCreateAuditFinding(programId: number, auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AuditFindingCreateInput) =>
      auditFindingsApi.create(programId, auditId, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: auditFindingsKey(programId, auditId) }),
  });
}

export function useUpdateAuditFinding(programId: number, auditId: number, findingId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AuditFindingUpdateInput) =>
      auditFindingsApi.update(programId, auditId, findingId, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: auditFindingsKey(programId, auditId) }),
  });
}

export function useDeleteAuditFinding(programId: number, auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (findingId: number) => auditFindingsApi.remove(programId, auditId, findingId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: auditFindingsKey(programId, auditId) }),
  });
}

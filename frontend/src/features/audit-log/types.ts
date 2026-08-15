export interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  actor_id: number | null;
  timestamp: string;
  diff: Record<string, unknown> | null;
}

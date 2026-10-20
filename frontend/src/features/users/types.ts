export interface ManagedUser {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  must_change_password: boolean;
  mfa_enabled: boolean;
}

export interface SecuritySettings {
  require_mfa_for_admins: boolean;
  /** Active administrators without two-step sign-in: who the rule would catch. */
  admins_without_mfa: number;
}

export interface TemporaryPassword {
  temporary_password: string;
}

export interface CreateUserInput {
  name: string;
  email: string;
  password: string;
  role: string;
}

export interface UpdateUserInput {
  role?: string;
  is_active?: boolean;
}

export interface DirectoryUser {
  id: number;
  name: string;
  /** Governance role names this user holds (Risk Owner, AI System Owner,
   * ...) -- see formatUserOption in this feature for how pickers show it. */
  governance_roles: string[];
}

/** What a user is personally accountable for. Read before deactivating them:
 * nobody may approve in their place, so anything they own is stuck until it
 * is reassigned. */
export interface UserAccountabilities {
  governance_roles: string[];
  ai_systems_owned: string[];
  datasets_owned: string[];
  open_risk_items: number;
}

export type ImportAction = "create" | "update" | "unchanged" | "skip";

export interface UserImportRow {
  line: number;
  name: string;
  email: string;
  role: string | null;
  action: ImportAction;
  note: string | null;
}

export interface UserImportMissing {
  id: number;
  name: string;
  email: string;
  role: string;
}

export interface UserImportPreview {
  rows: UserImportRow[];
  create: number;
  update: number;
  unchanged: number;
  skip: number;
  missing_from_file: UserImportMissing[];
}

export interface UserImportCreated {
  name: string;
  email: string;
  role: string;
  temporary_password: string;
}

/** The starting passwords are in here and nowhere else. */
export interface UserImportResult {
  created: UserImportCreated[];
  updated: number;
  unchanged: number;
  skipped: UserImportRow[];
  password_expires_on: string;
  missing_from_file: UserImportMissing[];
}

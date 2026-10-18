export interface ManagedUser {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  must_change_password: boolean;
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

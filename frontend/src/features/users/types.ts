export interface ManagedUser {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
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

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  /** True until the person replaces a temporary or outdated password; the
   * app shows only the change-password screen. */
  must_change_password: boolean;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

export interface SessionsEnded {
  other_sessions_ended: number;
}

export interface RegistrationStatus {
  registration_open: boolean;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

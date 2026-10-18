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
  /** Whether two-step sign-in is on for this account. */
  mfa_enabled: boolean;
  /** True while the organization requires it of this person and it isn't on
   * yet: the app then shows only the set-up screen. */
  mfa_setup_required: boolean;
}

/** What a correct password gets for an account with two-step sign-in: no
 * session yet, only a ticket to send with a code. */
export interface MfaChallenge {
  mfa_required: true;
  ticket: string;
}

export type LoginResult = AuthUser | MfaChallenge;

export function isMfaChallenge(result: LoginResult): result is MfaChallenge {
  return "mfa_required" in result && result.mfa_required === true;
}

export interface TwoStepLoginInput {
  ticket: string;
  code: string;
}

export interface TwoStepStatus {
  enabled: boolean;
  recovery_codes_remaining: number;
  setup_required: boolean;
}

export interface TwoStepSetup {
  secret: string;
  otpauth_uri: string;
}

export interface RecoveryCodes {
  recovery_codes: string[];
}

export interface TwoStepProof {
  password: string;
  code: string;
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
  /** True on a real deployment: the first account also needs the code from the
   * server's log (or the SETUP_CODE the operator configured). */
  setup_code_required: boolean;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
  setup_code?: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

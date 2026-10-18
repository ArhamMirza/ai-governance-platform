import type { ReactNode } from "react";

import { useCurrentUser, useLogout, useRegistrationStatus } from "../hooks";
import { ChangePasswordForm } from "./ChangePasswordForm";
import { TwoStepSetup } from "./TwoStepSetup";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";

const BrandMark = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4z" />
  </svg>
);

/** Shown instead of the app until a temporary or outdated password has been
 * replaced. The server enforces it too: every other route refuses this login. */
function ForcedPasswordChange() {
  const logout = useLogout();
  return (
    <div className="auth-screen">
      <div className="auth-form-panel">
        <div className="auth-card">
          <ChangePasswordForm forced />
          <button type="button" onClick={() => logout.mutate()} disabled={logout.isPending}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

/** Shown instead of the app while the organization requires two-step sign-in
 * of this administrator and it isn't on yet. The server enforces it too. */
function ForcedTwoStepSetup() {
  const logout = useLogout();
  return (
    <div className="auth-screen">
      <div className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-form">
            <h1>Set up two-step sign-in</h1>
            <p>
              Your organization requires two-step sign-in for administrators. Set it up to
              continue.
            </p>
            <TwoStepSetup />
          </div>
          <button type="button" onClick={() => logout.mutate()} disabled={logout.isPending}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * The sign-in / one-time-setup screen.
 *
 * A split panel: the left carries the platform's own voice, the right is
 * the form on the ordinary page ground. Both sides are sized to fit inside
 * one viewport with nothing scrolling -- this is a threshold someone passes
 * through, not a page to read down.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const { data: user, isLoading: userLoading, isSuccess } = useCurrentUser();
  const {
    data: registrationStatus,
    isLoading: statusLoading,
    isError: statusError,
  } = useRegistrationStatus();

  if (userLoading || (!isSuccess && statusLoading)) {
    return (
      <div className="auth-screen">
        <p className="auth-loading">Loading...</p>
      </div>
    );
  }

  if (isSuccess && user?.must_change_password) {
    return <ForcedPasswordChange />;
  }

  if (isSuccess && user?.mfa_setup_required) {
    return <ForcedTwoStepSetup />;
  }

  if (isSuccess && user) {
    return <>{children}</>;
  }

  // Not logged in, and the one check that decides which form to show
  // (whether registration is still open) never came back -- showing the
  // sign-in form here would be a silent guess, and on a fresh install with
  // no account yet it would strand someone with no way in at all.
  if (statusError) {
    return (
      <div className="auth-screen">
        <p className="auth-loading">Couldn't reach the server. Check your connection and reload.</p>
      </div>
    );
  }

  const isSetup = registrationStatus?.registration_open === true;

  return (
    <div className="auth-screen">
      <aside className="auth-brand-panel">
        <div className="auth-brand-panel-inner">
          <div className="auth-brand">
            <div className="sidebar-brand-mark">
              <BrandMark />
            </div>
            <div>
              <div className="auth-brand-name">Governance</div>
              <div className="auth-brand-sub">AI Compliance Platform</div>
            </div>
          </div>

          <h1 className="auth-pitch">
            Every AI system, <em>on the record.</em>
          </h1>
          <p className="auth-pitch-sub">
            What it is, what was assessed, who signed off, and when — one register instead
            of a folder of documents no one can trust is current.
          </p>
        </div>
      </aside>

      <div className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-brand auth-brand-compact">
            <div className="sidebar-brand-mark">
              <BrandMark />
            </div>
            <div>
              <div className="auth-brand-name">Governance</div>
              <div className="auth-brand-sub">AI Compliance Platform</div>
            </div>
          </div>

          {isSetup && <span className="auth-eyebrow">One-time setup</span>}
          {isSetup ? (
            <RegisterForm setupCodeRequired={registrationStatus?.setup_code_required === true} />
          ) : (
            <LoginForm />
          )}
        </div>
      </div>
    </div>
  );
}

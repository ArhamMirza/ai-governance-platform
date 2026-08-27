import type { ReactNode } from "react";

import { useCurrentUser, useRegistrationStatus } from "../hooks";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";

export function AuthGate({ children }: { children: ReactNode }) {
  const { data: user, isLoading: userLoading, isSuccess } = useCurrentUser();
  const { data: registrationStatus, isLoading: statusLoading } = useRegistrationStatus();

  if (userLoading || (!isSuccess && statusLoading)) {
    return (
      <div className="auth-screen">
        <p>Loading...</p>
      </div>
    );
  }

  if (isSuccess && user) {
    return <>{children}</>;
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="sidebar-brand-mark">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4z" />
            </svg>
          </div>
          <div>
            <div className="auth-brand-name">Governance</div>
            <div className="auth-brand-sub">AI Compliance Platform</div>
          </div>
        </div>
        {registrationStatus?.registration_open ? <RegisterForm /> : <LoginForm />}
      </div>
    </div>
  );
}

import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { AuthGate } from "../features/auth/components/AuthGate";
import { useCurrentUser } from "../features/auth/hooks";
import { EmployeeApp } from "../features/staff/components/EmployeeApp";
import { AppRoutes } from "./routes";
import { queryClient } from "./queryClient";

/** An employee login gets the staff home instead of the platform. Decided
 * here, inside the sign-in gate, so nothing of the platform is even rendered
 * for them. */
function SignedInApp() {
  const { data: user } = useCurrentUser();
  return user?.role === "employee" ? <EmployeeApp /> : <AppRoutes />;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthGate>
          <SignedInApp />
        </AuthGate>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

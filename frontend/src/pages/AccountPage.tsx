import { ChangePasswordForm } from "../features/auth/components/ChangePasswordForm";
import { useCurrentUser, useSignOutEverywhere } from "../features/auth/hooks";

/** Your own account: who you're signed in as, your password, and a way to
 * end every other session. Open to every signed-in role, employees included. */
export function AccountPage() {
  const { data: user } = useCurrentUser();
  const signOutEverywhere = useSignOutEverywhere();

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Your account</h1>
          <p>{user ? `${user.name} · ${user.email}` : ""}</p>
        </div>
      </div>

      <ChangePasswordForm />

      <h2>Signed in on other devices</h2>
      <p>
        Signs you out everywhere except this browser. Use it if you've used a shared computer or
        think someone else has your password.
      </p>
      <button onClick={() => signOutEverywhere.mutate()} disabled={signOutEverywhere.isPending}>
        {signOutEverywhere.isPending ? "Signing out..." : "Sign out of other devices"}
      </button>
      {signOutEverywhere.isSuccess && (
        <p role="status">
          {signOutEverywhere.data.other_sessions_ended === 0
            ? "You weren't signed in anywhere else."
            : `Signed out of ${signOutEverywhere.data.other_sessions_ended} other session(s).`}
        </p>
      )}
      {signOutEverywhere.isError && <p role="alert">Couldn't sign out of other devices.</p>}
    </section>
  );
}

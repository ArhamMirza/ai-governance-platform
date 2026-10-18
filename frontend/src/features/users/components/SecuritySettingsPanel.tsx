import { readError } from "../../../shared/api/readError";
import { useSecuritySettings, useUpdateSecuritySettings } from "../hooks";

/** Whether administrators must use two-step sign-in. Off to begin with, so
 * switching it on can't catch anyone by surprise: the count shows who it would
 * hold at the set-up screen. */
export function SecuritySettingsPanel() {
  const { data: settings, isLoading, isError } = useSecuritySettings();
  const update = useUpdateSecuritySettings();

  if (isLoading) return <p>Loading...</p>;
  if (isError || !settings) return <p role="alert">Couldn't load the sign-in security settings.</p>;

  return (
    <section aria-label="Sign-in security" className="security-settings">
      <h2>Sign-in security</h2>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={settings.require_mfa_for_admins}
          disabled={update.isPending}
          onChange={(e) => update.mutate(e.target.checked)}
        />
        Require two-step sign-in for administrators
      </label>
      <p className="field-hint">
        {settings.require_mfa_for_admins
          ? "Administrators without it are held at the set-up screen until they turn it on."
          : "Administrators can still choose to turn it on themselves."}{" "}
        {settings.admins_without_mfa === 0
          ? "Every active administrator has it on."
          : `${settings.admins_without_mfa} active administrator${
              settings.admins_without_mfa === 1 ? " hasn't" : "s haven't"
            } set it up yet.`}
      </p>
      {update.isError && <p role="alert">{readError(update.error, "Couldn't save the setting")}</p>}
    </section>
  );
}

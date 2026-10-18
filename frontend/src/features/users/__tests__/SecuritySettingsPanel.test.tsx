import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { SecuritySettingsPanel } from "../components/SecuritySettingsPanel";
import { useSecuritySettings, useUpdateSecuritySettings } from "../hooks";

vi.mock("../hooks");

function mockHooks(
  settings: { require_mfa_for_admins: boolean; admins_without_mfa: number } | undefined,
  { query = {}, update = {} }: { query?: object; update?: object } = {},
) {
  const mutate = vi.fn();
  vi.mocked(useSecuritySettings).mockReturnValue({
    data: settings,
    isLoading: false,
    isError: false,
    ...query,
  } as never);
  vi.mocked(useUpdateSecuritySettings).mockReturnValue({
    mutate,
    isPending: false,
    isError: false,
    ...update,
  } as never);
  return mutate;
}

describe("SecuritySettingsPanel", () => {
  it("shows the rule off, and who it would catch", () => {
    mockHooks({ require_mfa_for_admins: false, admins_without_mfa: 2 });

    render(<SecuritySettingsPanel />);

    expect(screen.getByLabelText("Require two-step sign-in for administrators")).not.toBeChecked();
    expect(screen.getByText(/Administrators can still choose to turn it on themselves/)).toBeInTheDocument();
    expect(screen.getByText(/2 active administrators haven't set it up yet/)).toBeInTheDocument();
  });

  it("says it in the singular too", () => {
    mockHooks({ require_mfa_for_admins: false, admins_without_mfa: 1 });

    render(<SecuritySettingsPanel />);

    expect(screen.getByText(/1 active administrator hasn't set it up yet/)).toBeInTheDocument();
  });

  it("says when everyone already has it", () => {
    mockHooks({ require_mfa_for_admins: true, admins_without_mfa: 0 });

    render(<SecuritySettingsPanel />);

    expect(screen.getByLabelText("Require two-step sign-in for administrators")).toBeChecked();
    expect(screen.getByText(/held at the set-up screen/)).toBeInTheDocument();
    expect(screen.getByText(/Every active administrator has it on/)).toBeInTheDocument();
  });

  it("switches the rule on and off", async () => {
    const mutate = mockHooks({ require_mfa_for_admins: false, admins_without_mfa: 0 });
    const user = userEvent.setup();

    const { rerender } = render(<SecuritySettingsPanel />);
    await user.click(screen.getByLabelText("Require two-step sign-in for administrators"));
    expect(mutate).toHaveBeenLastCalledWith(true);

    const mutateOff = mockHooks({ require_mfa_for_admins: true, admins_without_mfa: 0 });
    rerender(<SecuritySettingsPanel />);
    await user.click(screen.getByLabelText("Require two-step sign-in for administrators"));
    expect(mutateOff).toHaveBeenLastCalledWith(false);
  });

  it("shows why the server refused", () => {
    const error = new ApiError(
      409,
      JSON.stringify({ detail: "Turn on two-step sign-in for your own account first." }),
    );
    mockHooks({ require_mfa_for_admins: false, admins_without_mfa: 1 }, { update: { isError: true, error } });

    render(<SecuritySettingsPanel />);

    expect(screen.getByRole("alert")).toHaveTextContent("your own account first");
  });

  it("is disabled while saving", () => {
    mockHooks({ require_mfa_for_admins: false, admins_without_mfa: 1 }, { update: { isPending: true } });

    render(<SecuritySettingsPanel />);

    expect(screen.getByLabelText("Require two-step sign-in for administrators")).toBeDisabled();
  });

  it("copes with loading and with an error", () => {
    mockHooks(undefined, { query: { isLoading: true } });
    const { rerender } = render(<SecuritySettingsPanel />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();

    mockHooks(undefined, { query: { isError: true } });
    rerender(<SecuritySettingsPanel />);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load");
  });
});

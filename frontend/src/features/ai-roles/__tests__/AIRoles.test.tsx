import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { aiSystemLifecycleApi } from "../../ai-systems/api";
import { organizationContextApi } from "../../organization-context/api";
import type { OrganizationContext } from "../../organization-context/types";
import { aiRolesApi } from "../api";
import { AIRolePicker } from "../components/AIRolePicker";
import { AISystemAIRoles } from "../components/AISystemAIRoles";
import { OrganizationAIRoles } from "../components/OrganizationAIRoles";
import type { AIRole } from "../types";

vi.mock("../api");
vi.mock("../../ai-systems/api");
vi.mock("../../organization-context/api");

const ROLES: AIRole[] = [
  { code: "developer", label: "AI developer", parent: "AI producer", description: "Builds AI." },
  { code: "designer", label: "AI designer", parent: "AI producer", description: "Designs AI." },
  { code: "ai_user", label: "AI user", parent: "AI customer", description: "Uses AI." },
];

function renderWithProviders(ui: React.ReactNode) {
  vi.mocked(aiRolesApi.list).mockResolvedValue(ROLES);
  return render(<QueryClientProvider client={createTestQueryClient()}>{ui}</QueryClientProvider>);
}

function lifecycle(overrides = {}) {
  return {
    ai_system_row_id: 7,
    ai_roles: null,
    effective_ai_roles: ["developer"],
    is_archived: false,
    ...overrides,
  } as never;
}

describe("AIRolePicker", () => {
  it("groups the roles under their main role and toggles them", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(<AIRolePicker idPrefix="t" value={["developer"]} onChange={onChange} />);

    const producer = await screen.findByRole("group", { name: "AI producer" });
    expect(producer).toHaveTextContent("AI developer");
    expect(producer).toHaveTextContent("AI designer");
    expect(screen.getByRole("group", { name: "AI customer" })).toHaveTextContent("AI user");
    expect(screen.getByRole("checkbox", { name: /AI developer/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /AI user/ })).not.toBeChecked();

    await user.click(screen.getByRole("checkbox", { name: /AI user/ }));
    expect(onChange).toHaveBeenLastCalledWith(["developer", "ai_user"]);
    await user.click(screen.getByRole("checkbox", { name: /AI developer/ }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("keeps the ticks as given while controlled by its parent", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [value, setValue] = useState<string[]>([]);
      return <AIRolePicker idPrefix="t" value={value} onChange={setValue} />;
    }
    renderWithProviders(<Harness />);

    await user.click(await screen.findByRole("checkbox", { name: /AI designer/ }));

    expect(screen.getByRole("checkbox", { name: /AI designer/ })).toBeChecked();
  });
});

describe("OrganizationAIRoles", () => {
  it("saves the roles as each is ticked, sending only that field", async () => {
    vi.mocked(organizationContextApi.update).mockResolvedValue({} as OrganizationContext);
    const user = userEvent.setup();
    renderWithProviders(
      <OrganizationAIRoles context={{ ai_roles: ["developer"] } as OrganizationContext} />,
    );

    await user.click(await screen.findByRole("checkbox", { name: /AI user/ }));

    expect(organizationContextApi.update).toHaveBeenCalledWith({
      ai_roles: ["developer", "ai_user"],
    });
  });
});

describe("AISystemAIRoles", () => {
  it("follows the organization by default, showing its roles", async () => {
    vi.mocked(aiSystemLifecycleApi.get).mockResolvedValue(lifecycle());
    renderWithProviders(<AISystemAIRoles rowId={7} />);

    expect(await screen.findByText("AI developer")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Same as the organization" })).toBeChecked();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("starts its own roles from what it follows now", async () => {
    vi.mocked(aiSystemLifecycleApi.get).mockResolvedValue(lifecycle());
    vi.mocked(aiSystemLifecycleApi.setAIRoles).mockResolvedValue(lifecycle());
    const user = userEvent.setup();
    renderWithProviders(<AISystemAIRoles rowId={7} />);

    await user.click(await screen.findByRole("radio", { name: "Set for this system" }));

    expect(aiSystemLifecycleApi.setAIRoles).toHaveBeenCalledWith(7, { ai_roles: ["developer"] });
  });

  it("edits its own roles, and goes back to following the organization", async () => {
    vi.mocked(aiSystemLifecycleApi.get).mockResolvedValue(
      lifecycle({ ai_roles: ["ai_user"], effective_ai_roles: ["ai_user"] }),
    );
    vi.mocked(aiSystemLifecycleApi.setAIRoles).mockResolvedValue(lifecycle());
    const user = userEvent.setup();
    renderWithProviders(<AISystemAIRoles rowId={7} />);

    expect(await screen.findByRole("checkbox", { name: /AI user/ })).toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: /AI developer/ }));
    expect(aiSystemLifecycleApi.setAIRoles).toHaveBeenLastCalledWith(7, {
      ai_roles: ["ai_user", "developer"],
    });

    await user.click(screen.getByRole("radio", { name: "Same as the organization" }));
    expect(aiSystemLifecycleApi.setAIRoles).toHaveBeenLastCalledWith(7, { ai_roles: null });
  });

  it("can't be changed on an archived system", async () => {
    vi.mocked(aiSystemLifecycleApi.get).mockResolvedValue(lifecycle({ is_archived: true }));
    renderWithProviders(<AISystemAIRoles rowId={7} />);

    expect(await screen.findByRole("radio", { name: "Set for this system" })).toBeDisabled();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OrgChart } from "../components/OrgChart";
import { useOrgChart, useUpdateGovernanceRole } from "../hooks";
import type { OrgChartNode } from "../types";

vi.mock("../hooks");

const nodes: OrgChartNode[] = [
  {
    id: 1,
    name: "Chief AI Governance Officer",
    parent_role_id: null,
    max_holders: 1,
    holders: [{ id: 5, name: "Arham Mirza" }],
  },
  {
    id: 2,
    name: "Risk Owner",
    parent_role_id: 1,
    max_holders: null,
    holders: [{ id: 9, name: "Priya Shah" }],
  },
  { id: 3, name: "Data Owner", parent_role_id: 1, max_holders: null, holders: [] },
];

function mockHooks(update = vi.fn()) {
  vi.mocked(useOrgChart).mockReturnValue({
    data: nodes,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useUpdateGovernanceRole).mockReturnValue({
    mutateAsync: update,
    isPending: false,
  } as never);
  return update;
}

describe("OrgChart", () => {
  it("renders every role with its holder, or Vacant if unheld", () => {
    mockHooks();

    render(<OrgChart canManage={false} />);

    expect(screen.getByText("Chief AI Governance Officer")).toBeInTheDocument();
    expect(screen.getByText("Priya Shah")).toBeInTheDocument();
    expect(screen.getByText("Vacant")).toBeInTheDocument();
  });

  it("hides the reports-to control for a non-admin", () => {
    mockHooks();

    render(<OrgChart canManage={false} />);

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("lets an admin reparent a role from the chart", async () => {
    const update = mockHooks();
    const user = userEvent.setup();

    render(<OrgChart canManage />);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Data Owner reports to" }),
      "2",
    );

    await waitFor(() =>
      expect(update).toHaveBeenCalledWith({ roleId: 3, data: { parent_role_id: 2 } }),
    );
  });

  it("shows a placeholder when no roles are defined", () => {
    vi.mocked(useOrgChart).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);

    render(<OrgChart canManage={false} />);

    expect(screen.getByText("No governance roles defined yet.")).toBeInTheDocument();
  });
});

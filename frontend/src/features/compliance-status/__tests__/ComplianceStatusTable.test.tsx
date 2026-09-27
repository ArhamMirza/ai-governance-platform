import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ComplianceStatusTable } from "../components/ComplianceStatusTable";
import { useComplianceStatus } from "../hooks";
import type { ControlComplianceStatus } from "../types";

vi.mock("../hooks");

const controls: ControlComplianceStatus[] = [
  {
    id: 1,
    framework: "iso_42001",
    code: "5.2",
    title: "AI policy",
    description: null,
    category: "clause",
    status: "satisfied",
    reason: "Covered by 1 current record(s).",
    tagged_items: [
      {
        entity_type: "Policy",
        entity_id: 3,
        label: "Data Retention Policy",
        current: true,
        detail: "Policy approved and current",
      },
    ],
  },
  {
    id: 2,
    framework: "iso_42001",
    code: "8.4",
    title: "AI system impact assessment",
    description: null,
    category: "clause",
    status: "partial",
    reason: "1 of 1 tagged record(s) need attention: Policy is still in draft.",
    tagged_items: [
      {
        entity_type: "Policy",
        entity_id: 4,
        label: "Draft Policy",
        current: false,
        detail: "Policy is still in draft",
      },
    ],
  },
  {
    id: 3,
    framework: "iso_42001",
    code: "A.2.4",
    title: "Review of the AI policy",
    description: null,
    category: "annex_a_control",
    status: "no_coverage",
    reason: "Nothing in the system is tagged to this control yet.",
    tagged_items: [],
  },
];

function mockControls(data = controls) {
  vi.mocked(useComplianceStatus).mockReturnValue({
    data,
    isLoading: false,
    isError: false,
  } as never);
}

describe("ComplianceStatusTable", () => {
  it("lists every control with its computed status", () => {
    mockControls();

    render(<ComplianceStatusTable />);

    expect(screen.getByText("5.2")).toBeInTheDocument();
    expect(screen.getByText("satisfied")).toBeInTheDocument();
    expect(screen.getByText("partial")).toBeInTheDocument();
    expect(screen.getByText("no coverage")).toBeInTheDocument();
  });

  it("shows why a control is only partially covered", () => {
    mockControls();

    render(<ComplianceStatusTable />);

    expect(screen.getByText(/Policy is still in draft/)).toBeInTheDocument();
  });

  it("marks a stale tagged item distinctly from a current one", () => {
    mockControls();

    render(<ComplianceStatusTable />);

    expect(screen.getByText("Policy: Data Retention Policy")).toHaveAttribute(
      "data-current",
      "true",
    );
    expect(screen.getByText("Policy: Draft Policy")).toHaveAttribute("data-current", "false");
  });

  it("shows a placeholder for an uncovered control", () => {
    mockControls();

    render(<ComplianceStatusTable />);

    expect(screen.getByText("Not tagged to anything yet.")).toBeInTheDocument();
  });

  it("filters to only the gaps when asked", async () => {
    mockControls();
    const user = userEvent.setup();

    render(<ComplianceStatusTable />);
    await user.click(screen.getByLabelText("Show gaps only"));

    expect(screen.queryByText("5.2")).not.toBeInTheDocument();
    expect(screen.getByText("8.4")).toBeInTheDocument();
    expect(screen.getByText("A.2.4")).toBeInTheDocument();
  });

  it("scopes the query to the given framework", () => {
    mockControls();

    render(<ComplianceStatusTable framework="eu_ai_act" />);

    expect(useComplianceStatus).toHaveBeenCalledWith("eu_ai_act");
  });
});

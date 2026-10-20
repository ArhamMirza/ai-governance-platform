import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useSuppliers } from "../../suppliers/hooks";
import { useUserDirectory } from "../../users/hooks";
import { aiToolsApi } from "../api";
import { AIToolDetail } from "../components/AIToolDetail";
import { AIToolForm } from "../components/AIToolForm";
import { AIToolList } from "../components/AIToolList";
import { RequestQueue } from "../components/RequestQueue";
import { makeRequest, makeTool } from "./fixtures";

vi.mock("../api");
vi.mock("../../users/hooks");
vi.mock("../../suppliers/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderWithProviders(ui: React.ReactNode) {
  vi.mocked(useUserDirectory).mockReturnValue({
    data: [{ id: 3, name: "Elena Employee", governance_roles: [] }],
  } as never);
  vi.mocked(useSuppliers).mockReturnValue({ data: [{ id: 8, name: "Anthropic" }] } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AIToolList", () => {
  const tools = [
    makeTool({ id: 1, name: "Unapproved one" }),
    makeTool({
      id: 2,
      name: "Approved one",
      status: "approved",
      max_data_classification: "internal",
      review_due: "2027-01-01",
      domains: ["a.example", "b.example"],
    }),
    makeTool({
      id: 3,
      name: "Late one",
      status: "restricted",
      max_data_classification: "public",
      standing: { review_overdue: true },
    }),
    makeTool({ id: 4, name: "Withdrawn one", status: "revoked" }),
  ];

  it("lists every tool with its status, what it may be given, and flags only overdue reviews", async () => {
    vi.mocked(aiToolsApi.list).mockResolvedValue(tools);

    renderWithProviders(<AIToolList />);

    const rows = await screen.findAllByRole("row");
    const row = (text: string) => rows.find((r) => r.textContent?.includes(text))!;
    expect(rows).toHaveLength(5);
    expect(row("Unapproved one")).toHaveTextContent("Not approved");
    expect(row("Unapproved one")).toHaveTextContent("—");
    expect(row("Approved one")).toHaveTextContent("Internal data");
    expect(row("Approved one")).toHaveTextContent("a.example, b.example");
    expect(row("Approved one")).toHaveTextContent("2027-01-01");
    expect(row("Late one")).toHaveClass("row-flagged");
    expect(row("Late one")).toHaveTextContent("Review overdue");
    expect(row("Late one")).toHaveTextContent("Approved with limits");
    expect(row("Approved one")).not.toHaveClass("row-flagged");
    // A withdrawn tool shows no data allowance.
    expect(row("Withdrawn one")).toHaveTextContent("Access withdrawn");
    expect(row("Withdrawn one")).not.toHaveTextContent("data");
  });

  it("filters to what is allowed, not approved, or withdrawn", async () => {
    vi.mocked(aiToolsApi.list).mockResolvedValue(tools);
    const user = userEvent.setup();
    renderWithProviders(<AIToolList />);

    await user.selectOptions(await screen.findByLabelText("Show"), "allowed");
    expect(screen.getAllByRole("row").map((r) => r.textContent)).toEqual([
      expect.stringContaining("Tool"),
      expect.stringContaining("Approved one"),
      expect.stringContaining("Late one"),
    ]);

    await user.selectOptions(screen.getByLabelText("Show"), "catalogued");
    expect(screen.getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("Unapproved one")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Show"), "revoked");
    expect(screen.getByText("Withdrawn one")).toBeInTheDocument();
  });

  it("says when nothing matches", async () => {
    vi.mocked(aiToolsApi.list).mockResolvedValue([]);

    renderWithProviders(<AIToolList />);

    expect(await screen.findByText("No AI tools here.")).toBeInTheDocument();
  });
});

describe("AIToolForm", () => {
  it("adds a tool with its addresses split however they were typed", async () => {
    vi.mocked(aiToolsApi.create).mockResolvedValue(makeTool({ id: 9 }));
    const onCreated = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<AIToolForm onCreated={onCreated} />);

    await user.type(screen.getByLabelText("Tool"), "  Claude ");
    await user.type(screen.getByLabelText("Vendor"), "Anthropic");
    await user.type(
      screen.getByLabelText("Addresses"),
      "claude.ai, https://console.claude.ai/path{enter}api.claude.ai",
    );
    await user.click(screen.getByRole("button", { name: "Add Tool" }));

    expect(aiToolsApi.create).toHaveBeenCalledWith({
      name: "Claude",
      vendor: "Anthropic",
      kind: "web",
      domains: ["claude.ai", "https://console.claude.ai/path", "api.claude.ai"],
      description: null,
      owner_id: null,
      supplier_id: null,
    });
    expect(onCreated).toHaveBeenCalledWith(9);
  });

  it("adds a tool that isn't a website with no addresses at all", async () => {
    vi.mocked(aiToolsApi.create).mockResolvedValue(makeTool({ id: 4, kind: "local_model" }));
    const user = userEvent.setup();
    renderWithProviders(<AIToolForm />);

    await user.type(screen.getByLabelText("Tool"), "Ollama");
    await user.selectOptions(
      screen.getByLabelText("What kind of tool"),
      "Model run on our own machines",
    );
    // There is nothing for the browser to watch, so no address to ask for.
    expect(screen.queryByLabelText("Addresses")).not.toBeInTheDocument();
    expect(screen.getByText(/can't see this kind of tool/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add Tool" }));

    expect(aiToolsApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Ollama", kind: "local_model", domains: [] }),
    );
  });

  it("needs a name and at least one address", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AIToolForm />);

    await user.type(screen.getByLabelText("Addresses"), " , ,  ");
    await user.click(screen.getByRole("button", { name: "Add Tool" }));

    expect(await screen.findByText("What is the tool called?")).toBeInTheDocument();
    expect(screen.getByText("Add at least one address")).toBeInTheDocument();
    expect(aiToolsApi.create).not.toHaveBeenCalled();
  });
});

describe("AIToolDetail", () => {
  it("offers approving or limiting a tool that isn't approved, with the data it may be given", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool());
    vi.mocked(aiToolsApi.decide).mockResolvedValue(makeTool());
    const user = userEvent.setup();
    renderWithProviders(<AIToolDetail toolId={1} />);

    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve with Limits" })).toBeInTheDocument();
    // Nothing to withdraw from a tool that was never approved.
    expect(screen.queryByRole("button", { name: "Withdraw Access" })).not.toBeInTheDocument();

    await user.selectOptions(
      screen.getByLabelText("The most sensitive data it may be given"),
      "confidential",
    );
    await user.type(screen.getByLabelText("Conditions of use"), "  Company accounts only  ");
    await user.type(screen.getByLabelText(/Review by/), "2027-03-01");
    await user.click(screen.getByRole("button", { name: "Approve" }));

    expect(aiToolsApi.decide).toHaveBeenCalledWith(1, {
      action: "approve",
      max_data_classification: "confidential",
      conditions_of_use: "Company accounts only",
      review_due: "2027-03-01",
      note: null,
    });
  });

  it("needs a reason to withdraw access, and sends nothing about data with it", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(
      makeTool({ status: "approved", conditions_of_use: "Work accounts" }),
    );
    vi.mocked(aiToolsApi.decide).mockResolvedValue(makeTool());
    const user = userEvent.setup();
    renderWithProviders(<AIToolDetail toolId={1} />);

    const withdraw = await screen.findByRole("button", { name: "Withdraw Access" });
    expect(withdraw).toBeDisabled();
    await user.type(screen.getByLabelText(/Note \(needed to withdraw/), "   ");
    expect(withdraw).toBeDisabled();
    await user.type(screen.getByLabelText(/Note \(needed to withdraw/), "Vendor breach");
    // A review date typed for approving doesn't go with withdrawing.
    await user.type(screen.getByLabelText(/Review by/), "2027-03-01");
    await user.click(withdraw);

    expect(aiToolsApi.decide).toHaveBeenCalledWith(1, {
      action: "revoke",
      max_data_classification: null,
      conditions_of_use: null,
      review_due: null,
      note: "Vendor breach",
    });
  });

  it("offers the other decisions from each status", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool({ status: "approved" }));
    const approved = renderWithProviders(<AIToolDetail toolId={1} />);
    expect(await screen.findByRole("button", { name: "Approve with Limits" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdraw Access" })).toBeInTheDocument();
    // Already approved: nothing to approve again.
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    approved.unmount();

    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool({ status: "restricted" }));
    const { unmount } = renderWithProviders(<AIToolDetail toolId={1} />);
    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdraw Access" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve with Limits" })).not.toBeInTheDocument();
    unmount();

    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool({ status: "revoked" }));
    renderWithProviders(<AIToolDetail toolId={1} />);
    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Withdraw Access" })).not.toBeInTheDocument();
  });

  it("shows when it was last decided and flags an overdue review", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(
      makeTool({
        status: "approved",
        decided_on: "2026-05-01",
        decision_note: "Fine for research",
        review_due: "2026-06-01",
        standing: { review_overdue: true },
      }),
    );

    renderWithProviders(<AIToolDetail toolId={1} />);

    expect(await screen.findByText("Review overdue")).toBeInTheDocument();
    expect(screen.getByText("Last decided 2026-05-01: Fine for research")).toBeInTheDocument();
    expect(screen.getByText(/review by 2026-06-01/)).toBeInTheDocument();
  });

  it("saves an edited address list only when it changed, and never an empty one", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool());
    vi.mocked(aiToolsApi.update).mockResolvedValue(makeTool());
    const user = userEvent.setup();
    renderWithProviders(<AIToolDetail toolId={1} />);

    const box = await screen.findByLabelText("Addresses");
    await user.click(box);
    await user.tab();
    expect(aiToolsApi.update).not.toHaveBeenCalled();

    await user.clear(box);
    await user.tab();
    expect(aiToolsApi.update).not.toHaveBeenCalled();

    await user.type(box, "claude.ai{enter}console.claude.ai");
    await user.tab();
    expect(aiToolsApi.update).toHaveBeenCalledWith(1, {
      domains: ["claude.ai", "console.claude.ai"],
    });
  });

  it("never saves a blank name", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool());
    const user = userEvent.setup();
    renderWithProviders(<AIToolDetail toolId={1} />);

    const name = await screen.findByLabelText("Tool");
    await user.clear(name);
    await user.type(name, "   ");
    await user.tab();

    expect(aiToolsApi.update).not.toHaveBeenCalled();
  });

  it("links a supplier record and an owner", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool());
    vi.mocked(aiToolsApi.update).mockResolvedValue(makeTool());
    const user = userEvent.setup();
    renderWithProviders(<AIToolDetail toolId={1} />);

    await user.selectOptions(await screen.findByLabelText("Supplier record"), "8");
    expect(aiToolsApi.update).toHaveBeenLastCalledWith(1, { supplier_id: 8 });
    await user.selectOptions(screen.getByLabelText("Owner"), "3");
    expect(aiToolsApi.update).toHaveBeenLastCalledWith(1, { owner_id: 3 });
  });

  it("only lets a tool nobody has decided on be deleted", async () => {
    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool());
    const { unmount } = renderWithProviders(<AIToolDetail toolId={1} />);
    expect(await screen.findByRole("button", { name: "Delete Tool" })).toBeInTheDocument();
    unmount();

    vi.mocked(aiToolsApi.get).mockResolvedValue(makeTool({ status: "revoked", decided_on: "2026-05-01" }));
    renderWithProviders(<AIToolDetail toolId={1} />);
    expect(await screen.findByText(/Withdraw access instead of deleting it/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Tool" })).not.toBeInTheDocument();
  });
});

describe("RequestQueue", () => {
  it("shows who asked and why, waiting requests first", async () => {
    vi.mocked(aiToolsApi.listRequests).mockResolvedValue([
      makeRequest({ id: 1, tool_name: "Old answer", status: "rejected", decided_on: "2026-05-20", decision_note: "No DPA" }),
      makeRequest({ id: 2, tool_name: "Waiting one", data_involved: "Public pages" }),
    ]);

    renderWithProviders(<RequestQueue />);

    expect(await screen.findByText(/Waiting for a decision \(1\)/)).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Waiting one");
    expect(items[0]).toHaveTextContent("Asked by Elena Employee on 2026-06-01");
    expect(items[0]).toHaveTextContent("Data it would touch: Public pages");
    expect(items[1]).toHaveTextContent("Old answer");
    expect(items[1]).toHaveTextContent("Answered 2026-05-20: No DPA");
    // An answered request has no form.
    expect(within(items[1]).queryByRole("button")).not.toBeInTheDocument();
  });

  it("approves a request with the data it may be given and the conditions", async () => {
    vi.mocked(aiToolsApi.listRequests).mockResolvedValue([makeRequest()]);
    vi.mocked(aiToolsApi.decideRequest).mockResolvedValue(makeRequest());
    const user = userEvent.setup();
    renderWithProviders(<RequestQueue />);

    await user.selectOptions(await screen.findByLabelText("Most sensitive data it may be given"), "public");
    await user.type(screen.getByLabelText("Conditions of use"), "No customer data");
    await user.click(screen.getByRole("button", { name: "Approve Perplexity" }));

    expect(aiToolsApi.decideRequest).toHaveBeenCalledWith(1, {
      action: "approve",
      domain: null,
      max_data_classification: "public",
      conditions_of_use: "No customer data",
      review_due: null,
      note: null,
    });
  });

  it("needs a reason to say no, and sends no data allowance with it", async () => {
    vi.mocked(aiToolsApi.listRequests).mockResolvedValue([makeRequest()]);
    vi.mocked(aiToolsApi.decideRequest).mockResolvedValue(makeRequest());
    const user = userEvent.setup();
    renderWithProviders(<RequestQueue />);

    const no = await screen.findByRole("button", { name: "Say No" });
    expect(no).toBeDisabled();
    await user.type(screen.getByLabelText(/Note to the employee/), "Data leaves the EU");
    await user.click(no);

    expect(aiToolsApi.decideRequest).toHaveBeenCalledWith(1, {
      action: "reject",
      domain: null,
      max_data_classification: null,
      conditions_of_use: null,
      review_due: null,
      note: "Data leaves the EU",
    });
  });

  it("asks for an address only when the request has none and names no catalogued tool", async () => {
    vi.mocked(aiToolsApi.listRequests).mockResolvedValue([
      makeRequest({ id: 1, tool_name: "Mystery AI", domain: null }),
      makeRequest({ id: 2, tool_name: "Has address" }),
      makeRequest({ id: 3, tool_name: "In catalogue", domain: null, tool_id: 5 }),
    ]);
    vi.mocked(aiToolsApi.decideRequest).mockResolvedValue(makeRequest());
    const user = userEvent.setup();
    renderWithProviders(<RequestQueue />);

    const approve = await screen.findByRole("button", { name: "Approve Mystery AI" });
    expect(screen.getAllByLabelText("Address to allow")).toHaveLength(1);
    expect(approve).toBeDisabled();
    await user.type(screen.getByLabelText("Address to allow"), " mystery.ai ");
    await user.click(approve);

    expect(aiToolsApi.decideRequest).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ action: "approve", domain: "mystery.ai" }),
    );
    expect(screen.getByRole("button", { name: "Approve Has address" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Approve In catalogue" })).toBeEnabled();
  });

  it("says when no one has asked", async () => {
    vi.mocked(aiToolsApi.listRequests).mockResolvedValue([]);

    renderWithProviders(<RequestQueue />);

    expect(await screen.findByText("No one has asked for a tool yet.")).toBeInTheDocument();
  });
});

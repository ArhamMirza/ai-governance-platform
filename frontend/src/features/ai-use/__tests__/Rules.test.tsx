import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { dlpRulesApi } from "../api";
import { DLPRuleForm } from "../components/DLPRuleForm";
import { DLPRuleList } from "../components/DLPRuleList";
import { RuleTester } from "../components/RuleTester";
import { DETECTORS, makeRule } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  vi.mocked(dlpRulesApi.detectors).mockResolvedValue(DETECTORS);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DLPRuleList", () => {
  const rules = [
    makeRule({ id: 1 }),
    makeRule({
      id: 2,
      name: "Client names",
      description: "Never to leave the building",
      kind: "keywords",
      builtin_key: null,
      keywords: ["Project Falcon", "Acme Corp"],
      classification: "internal",
      action: "warn",
      enabled: false,
    }),
    makeRule({
      id: 3,
      name: "Ticket numbers",
      kind: "regex",
      builtin_key: null,
      pattern: String.raw`\bPROJ-\d{4}\b`,
      action: "monitor",
    }),
  ];

  it("describes what each rule looks for without printing the words themselves", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);

    renderWithProviders(<DLPRuleList />);

    const rows = await screen.findAllByRole("row");
    const row = (name: string) => rows.find((r) => r.textContent?.includes(name))!;
    expect(row("Payment card numbers")).toHaveTextContent("Built-in detector");
    expect(row("Payment card numbers")).toHaveTextContent("Payment card number");
    expect(row("Client names")).toHaveTextContent("2 words or phrases");
    expect(row("Client names")).not.toHaveTextContent("Falcon");
    expect(row("Client names")).toHaveTextContent("Never to leave the building");
    expect(row("Ticket numbers")).toHaveTextContent(String.raw`\bPROJ-\d{4}\b`);
    expect(row("Client names")).toHaveClass("row-muted");
    expect(row("Payment card numbers")).not.toHaveClass("row-muted");
  });

  it("changes the action, the data class and whether it is on, straight from the list", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    vi.mocked(dlpRulesApi.update).mockResolvedValue(rules[0]);
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleList />);

    await user.selectOptions(await screen.findByLabelText("Action for Payment card numbers"), "warn");
    expect(dlpRulesApi.update).toHaveBeenLastCalledWith(1, { action: "warn" });
    await user.selectOptions(screen.getByLabelText("Data class for Payment card numbers"), "internal");
    expect(dlpRulesApi.update).toHaveBeenLastCalledWith(1, { classification: "internal" });
    await user.click(screen.getByLabelText("Switch on Client names"));
    expect(dlpRulesApi.update).toHaveBeenLastCalledWith(2, { enabled: true });
  });

  it("opens the definition for editing, and saves a field only when it changed", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    vi.mocked(dlpRulesApi.update).mockResolvedValue(rules[1]);
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleList />);

    const row = (await screen.findAllByRole("row")).find((r) => r.textContent?.includes("Client names"))!;
    await user.click(within(row).getByRole("button", { name: "Edit" }));
    const words = await screen.findByLabelText("Words and phrases");
    expect(words).toHaveValue("Project Falcon\nAcme Corp");
    await user.click(words);
    await user.tab();
    expect(dlpRulesApi.update).not.toHaveBeenCalled();

    await user.type(words, "\nOsprey, Heron");
    await user.tab();
    expect(dlpRulesApi.update).toHaveBeenCalledWith(2, {
      keywords: ["Project Falcon", "Acme Corp", "Osprey", "Heron"],
    });
  });

  it("never saves a blank name", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue([rules[0]]);
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleList />);

    await user.click(await screen.findByRole("button", { name: "Edit" }));
    const name = await screen.findByLabelText("Rule");
    await user.clear(name);
    await user.tab();

    expect(dlpRulesApi.update).not.toHaveBeenCalled();
  });

  it("edits a pattern and a built-in detector", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue([rules[2], rules[0]]);
    vi.mocked(dlpRulesApi.update).mockResolvedValue(rules[0]);
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleList />);

    const buttons = await screen.findAllByRole("button", { name: "Edit" });
    await user.click(buttons[0]);
    const pattern = await screen.findByLabelText("Pattern");
    await user.clear(pattern);
    // Pasted: typing treats [ and { as key names.
    await user.click(pattern);
    await user.paste("TKT-[0-9]+");
    await user.tab();
    expect(dlpRulesApi.update).toHaveBeenCalledWith(3, { pattern: "TKT-[0-9]+" });

    await user.click(screen.getAllByRole("button", { name: /Edit|Close/ })[1]);
    await user.selectOptions(await screen.findByLabelText("Detector"), "api_key");
    expect(dlpRulesApi.update).toHaveBeenLastCalledWith(1, { builtin_key: "api_key" });
  });

  it("asks before deleting, and says why when the server refuses an edit", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue([rules[2]]);
    vi.mocked(dlpRulesApi.update).mockRejectedValue(
      new ApiError(400, JSON.stringify({ detail: "A repeated group that itself repeats can freeze the page." })),
    );
    vi.mocked(dlpRulesApi.remove).mockResolvedValue();
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleList />);

    await user.click(await screen.findByRole("button", { name: "Delete" }));
    expect(dlpRulesApi.remove).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(dlpRulesApi.remove).toHaveBeenCalledWith(3);
    expect(confirm).toHaveBeenCalledTimes(2);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const pattern = await screen.findByLabelText("Pattern");
    await user.clear(pattern);
    await user.click(pattern);
    await user.paste("(a+)+");
    await user.tab();
    expect(await screen.findByRole("alert")).toHaveTextContent("can freeze the page");
    confirm.mockRestore();
  });

  it("says when there are no rules", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue([]);

    renderWithProviders(<DLPRuleList />);

    expect(await screen.findByText(/No rules yet/)).toBeInTheDocument();
  });
});

describe("DLPRuleForm", () => {
  it("adds a built-in rule, showing what the detector catches", async () => {
    vi.mocked(dlpRulesApi.create).mockResolvedValue(makeRule({ id: 9 }));
    const onCreated = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleForm onCreated={onCreated} />);

    await user.type(screen.getByLabelText("Rule"), "Cards");
    await screen.findByRole("option", { name: "Payment card number" });
    await user.selectOptions(screen.getByLabelText("Detector"), "credit_card");
    expect(screen.getByText("13 to 19 digits.")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("When it matches"), "block");
    await user.click(screen.getByRole("button", { name: "Add Rule" }));

    expect(dlpRulesApi.create).toHaveBeenCalledWith({
      name: "Cards",
      description: null,
      kind: "builtin",
      builtin_key: "credit_card",
      keywords: null,
      pattern: null,
      classification: "confidential",
      action: "block",
      enabled: true,
    });
    expect(onCreated).toHaveBeenCalledWith(9);
  });

  it("adds a keyword rule from a list typed one per line", async () => {
    vi.mocked(dlpRulesApi.create).mockResolvedValue(makeRule());
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleForm />);

    await user.type(screen.getByLabelText("Rule"), "Clients");
    await user.selectOptions(screen.getByLabelText("What it looks for"), "keywords");
    expect(screen.queryByLabelText("Detector")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Words and phrases"), "Project Falcon{enter}Acme Corp, Osprey");
    await user.selectOptions(screen.getByLabelText("How sensitive the data is"), "internal");
    await user.click(screen.getByRole("button", { name: "Add Rule" }));

    expect(dlpRulesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "keywords",
        builtin_key: null,
        keywords: ["Project Falcon", "Acme Corp", "Osprey"],
        pattern: null,
        classification: "internal",
      }),
    );
  });

  it("sends no detector for a rule that is not a built-in one, even if one was picked first", async () => {
    vi.mocked(dlpRulesApi.create).mockResolvedValue(makeRule());
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleForm />);

    await user.type(screen.getByLabelText("Rule"), "Clients");
    await screen.findByRole("option", { name: "Payment card number" });
    await user.selectOptions(screen.getByLabelText("Detector"), "credit_card");
    await user.selectOptions(screen.getByLabelText("What it looks for"), "keywords");
    await user.type(screen.getByLabelText("Words and phrases"), "Project Falcon");
    await user.click(screen.getByRole("button", { name: "Add Rule" }));

    expect(dlpRulesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "keywords", builtin_key: null }),
    );
  });

  it("adds a pattern rule", async () => {
    vi.mocked(dlpRulesApi.create).mockResolvedValue(makeRule());
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleForm />);

    await user.type(screen.getByLabelText("Rule"), "Tickets");
    await user.selectOptions(screen.getByLabelText("What it looks for"), "regex");
    await user.click(screen.getByLabelText("Pattern"));
    await user.paste(String.raw`PROJ-\d{4}`);
    await user.click(screen.getByRole("button", { name: "Add Rule" }));

    expect(dlpRulesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "regex", pattern: String.raw`PROJ-\d{4}`, keywords: null }),
    );
  });

  it("asks for what the chosen kind needs", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleForm />);

    await user.click(screen.getByRole("button", { name: "Add Rule" }));
    expect(await screen.findByText("Name the rule")).toBeInTheDocument();
    expect(screen.getByText("Choose what to look for")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("What it looks for"), "keywords");
    await user.type(screen.getByLabelText("Words and phrases"), " , ");
    await user.click(screen.getByRole("button", { name: "Add Rule" }));
    expect(await screen.findByText("Add at least one word or phrase")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("What it looks for"), "regex");
    await user.click(screen.getByRole("button", { name: "Add Rule" }));
    expect(await screen.findByText("Enter the pattern")).toBeInTheDocument();
    expect(dlpRulesApi.create).not.toHaveBeenCalled();
  });

  it("says why when the server refuses a pattern", async () => {
    vi.mocked(dlpRulesApi.create).mockRejectedValue(
      new ApiError(400, JSON.stringify({ detail: "Back-references aren't allowed." })),
    );
    const user = userEvent.setup();
    renderWithProviders(<DLPRuleForm />);

    await user.type(screen.getByLabelText("Rule"), "Echo");
    await user.selectOptions(screen.getByLabelText("What it looks for"), "regex");
    await user.click(screen.getByLabelText("Pattern"));
    await user.paste(String.raw`(\w)\1`);
    await user.click(screen.getByRole("button", { name: "Add Rule" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Back-references aren't allowed.");
  });
});

describe("RuleTester", () => {
  const rules = [
    makeRule({ id: 1, action: "block" }),
    makeRule({
      id: 2,
      name: "Client names",
      kind: "keywords",
      builtin_key: null,
      keywords: ["Project Falcon"],
      classification: "internal",
      action: "warn",
    }),
    makeRule({ id: 3, name: "Switched off", enabled: false, action: "block" }),
  ];

  it("shows which rules would act on the text, strictest first, with the match masked", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    const user = userEvent.setup();
    renderWithProviders(<RuleTester />);

    await screen.findByLabelText("Text to check");
    await user.click(screen.getByLabelText("Text to check"));
    await user.paste("Project Falcon budget, card 4111111111111111 and another 5500005555555559");

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Payment card numbers -- block");
    expect(items[0]).toHaveTextContent("Found 2 times: 41••••••••••••11, 55••••••••••••59");
    expect(items[1]).toHaveTextContent("Client names -- warn");
    expect(items[1]).toHaveTextContent("Found 1 time: Pr••••••••••on");
    // The real number is never printed back.
    expect(screen.queryByText(/4111111111111111/, { selector: "li *" })).not.toBeInTheDocument();
  });

  it("ignores rules that are switched off", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    const user = userEvent.setup();
    renderWithProviders(<RuleTester />);

    await user.click(await screen.findByLabelText("Text to check"));
    await user.paste("4111111111111111");

    const items = await screen.findAllByRole("listitem");
    expect(items.map((item) => item.textContent)).not.toContain(expect.stringContaining("Switched off"));
  });

  it("holds a tool only to rules about data it isn't cleared for", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    const user = userEvent.setup();
    renderWithProviders(<RuleTester />);

    await user.click(await screen.findByLabelText("Text to check"));
    await user.paste("Project Falcon and 4111111111111111");
    expect(await screen.findAllByRole("listitem")).toHaveLength(2);

    await user.selectOptions(screen.getByLabelText("Tool the text is going into"), "internal");
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("listitem")).toHaveTextContent("Payment card numbers");

    await user.selectOptions(screen.getByLabelText("Tool the text is going into"), "confidential");
    expect(screen.getByRole("status")).toHaveTextContent("Nothing in this text would be stopped");
  });

  it("says nothing until there is text, and says so when the text is clean", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    const user = userEvent.setup();
    renderWithProviders(<RuleTester />);

    await screen.findByLabelText("Text to check");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await user.click(screen.getByLabelText("Text to check"));
    await user.paste("Please summarise this article about gardening.");

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Nothing in this text would be stopped or flagged.",
    );
  });

  it("promises that the text stays in the browser, and keeps the promise", async () => {
    vi.mocked(dlpRulesApi.list).mockResolvedValue(rules);
    const user = userEvent.setup();
    renderWithProviders(<RuleTester />);

    expect(await screen.findByText(/What you type here is not sent to the server/)).toBeInTheDocument();
    await user.click(screen.getByLabelText("Text to check"));
    await user.paste("4111111111111111");

    // Only reading the rules; nothing is posted anywhere.
    expect(dlpRulesApi.create).not.toHaveBeenCalled();
    expect(dlpRulesApi.update).not.toHaveBeenCalled();
  });
});

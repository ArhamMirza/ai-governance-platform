import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { usersApi } from "../api";
import { ImportUsersPanel } from "../components/ImportUsersPanel";
import type { UserImportPreview, UserImportResult } from "../types";

vi.mock("../api");

const PREVIEW: UserImportPreview = {
  rows: [
    {
      line: 2,
      name: "Elena Ortiz",
      email: "elena@example.com",
      role: "employee",
      action: "create",
      note: null,
    },
    {
      line: 3,
      name: "Pat Promote",
      email: "pat@example.com",
      role: "contributor",
      action: "update",
      note: "Changes role viewer to contributor.",
    },
    {
      line: 4,
      name: "Eve",
      email: "eve@example.com",
      role: "admin",
      action: "skip",
      note: "Administrators are created one at a time on the Users page.",
    },
  ],
  create: 1,
  update: 1,
  unchanged: 0,
  skip: 1,
  missing_from_file: [
    { id: 9, name: "Leaver Lee", email: "leaver@example.com", role: "viewer" },
  ],
};

const RESULT: UserImportResult = {
  created: [
    {
      name: "Elena Ortiz",
      email: "elena@example.com",
      role: "employee",
      temporary_password: "Xk3mPq9rT2vL",
    },
    {
      name: "=Evil",
      email: "evil@example.com",
      role: "viewer",
      temporary_password: "Ab4cDe5fGh6J",
    },
  ],
  updated: 1,
  unchanged: 0,
  skipped: [
    {
      line: 4,
      name: "Eve",
      email: "eve@example.com",
      role: "admin",
      action: "skip",
      note: "Administrators are created one at a time on the Users page.",
    },
  ],
  password_expires_on: "2026-10-27",
  missing_from_file: [],
};

function renderPanel(onClose = vi.fn()) {
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <ImportUsersPanel onClose={onClose} />
    </QueryClientProvider>,
  );
  return onClose;
}

async function chooseFile(user: ReturnType<typeof userEvent.setup>) {
  const file = new File(
    ["name,email\nElena,elena@example.com\n"],
    "staff.csv",
    { type: "text/csv" },
  );
  await user.upload(screen.getByLabelText("CSV file"), file);
  return file;
}

describe("ImportUsersPanel", () => {
  beforeEach(() => {
    vi.mocked(usersApi.previewImport).mockResolvedValue(PREVIEW);
    vi.mocked(usersApi.runImport).mockResolvedValue(RESULT);
  });

  afterEach(() => vi.restoreAllMocks());

  it("can't preview until a file is chosen", () => {
    renderPanel();

    expect(screen.getByRole("button", { name: "Preview" })).toBeDisabled();
  });

  it("shows what would happen to each line, and creates nothing yet", async () => {
    const user = userEvent.setup();
    renderPanel();
    const file = await chooseFile(user);

    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByText(/to add/)).toHaveTextContent(
      "1 to add, 1 to update, 0 already",
    );
    expect(usersApi.previewImport).toHaveBeenCalledWith(file);
    expect(usersApi.runImport).not.toHaveBeenCalled();
    const rows = screen.getAllByRole("row").map((row) => row.textContent);
    expect(rows).toContainEqual(
      expect.stringContaining("Changes role viewer to contributor."),
    );
    expect(rows).toContainEqual(
      expect.stringContaining("Administrators are created one at a time"),
    );
    // Someone in the system but not the file is only mentioned.
    expect(screen.getByText("Leaver Lee")).toBeInTheDocument();
    expect(screen.getByText(/Nothing is done about these/)).toBeInTheDocument();
  });

  it("says what the import will do, and is switched off when it would do nothing", async () => {
    const user = userEvent.setup();
    renderPanel();
    await chooseFile(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    expect(
      await screen.findByRole("button", { name: "Add 1 and update 1" }),
    ).toBeEnabled();

    vi.mocked(usersApi.previewImport).mockResolvedValue({
      ...PREVIEW,
      create: 0,
      update: 0,
      unchanged: 2,
      skip: 0,
      rows: [],
    });
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(
      await screen.findByRole("button", { name: "Add 0 and update 0" }),
    ).toBeDisabled();
  });

  it("shows the starting passwords once the import has run, with when they stop working", async () => {
    const user = userEvent.setup();
    renderPanel();
    await chooseFile(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(
      await screen.findByRole("button", { name: "Add 1 and update 1" }),
    );

    expect(
      await screen.findByText("2 accounts added, 1 updated"),
    ).toBeInTheDocument();
    expect(screen.getByText("Xk3mPq9rT2vL")).toBeInTheDocument();
    expect(screen.getByText(/starting passwords are shown/)).toHaveTextContent("once");
    expect(screen.getByText(/stops working on 2026-10-27/)).toBeInTheDocument();
    expect(screen.getByText(/Line 4: eve@example.com/)).toBeInTheDocument();
  });

  it("downloads the passwords as a CSV that a spreadsheet won't run as a formula", async () => {
    let saved = "";
    const createObjectURL = vi.fn((blob: Blob) => {
      void blob.text().then((text) => (saved = text));
      return "blob:x";
    });
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      () => undefined,
    );
    const user = userEvent.setup();
    renderPanel();
    await chooseFile(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(
      await screen.findByRole("button", { name: "Add 1 and update 1" }),
    );

    await user.click(
      await screen.findByRole("button", { name: "Download as CSV" }),
    );

    await waitFor(() => expect(saved).not.toBe(""));
    const lines = saved.trim().split("\n");
    expect(lines[0]).toBe("name,email,role,temporary password,works until");
    expect(lines[1]).toBe(
      '"Elena Ortiz","elena@example.com","employee","Xk3mPq9rT2vL","2026-10-27"',
    );
    // A name that starts like a formula is neutralised.
    expect(lines[2]).toBe(
      `"'=Evil","evil@example.com","viewer","Ab4cDe5fGh6J","2026-10-27"`,
    );
    vi.unstubAllGlobals();
  });

  it("forgets the passwords when it is closed", async () => {
    const user = userEvent.setup();
    const onClose = renderPanel();
    await chooseFile(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(
      await screen.findByRole("button", { name: "Add 1 and update 1" }),
    );
    await screen.findByText("Xk3mPq9rT2vL");

    await user.click(screen.getByRole("button", { name: "Done" }));

    expect(onClose).toHaveBeenCalled();
  });

  it("says why a file was refused", async () => {
    vi.mocked(usersApi.previewImport).mockRejectedValue(
      new ApiError(400, JSON.stringify({ detail: "That file is empty." })),
    );
    const user = userEvent.setup();
    renderPanel();
    await chooseFile(user);

    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That file is empty.",
    );
    expect(screen.queryByText(/to add/)).not.toBeInTheDocument();
  });

  it("drops an old preview when a different file is chosen", async () => {
    const user = userEvent.setup();
    renderPanel();
    await chooseFile(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await screen.findByText(/to add/);

    await user.upload(
      screen.getByLabelText("CSV file"),
      new File(["x"], "other.csv", { type: "text/csv" }),
    );

    expect(screen.queryByText(/to add/)).not.toBeInTheDocument();
    expect(
      within(document.body).queryByRole("button", { name: /Add \d/ }),
    ).not.toBeInTheDocument();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RecoveryCodesView } from "../components/RecoveryCodesView";

const CODES = ["ABCDE-FGHJK", "MNPQR-STUVW"];

afterEach(() => {
  vi.restoreAllMocks();
});

describe("RecoveryCodesView", () => {
  it("lists every code", () => {
    render(<RecoveryCodesView codes={CODES} onDone={vi.fn()} />);

    const list = screen.getByRole("list", { name: "Recovery codes" });
    expect(list).toHaveTextContent("ABCDE-FGHJK");
    expect(list).toHaveTextContent("MNPQR-STUVW");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("will not let you leave until you say they are saved", async () => {
    const onDone = vi.fn();
    const user = userEvent.setup();

    render(<RecoveryCodesView codes={CODES} onDone={onDone} />);
    const done = screen.getByRole("button", { name: "Done" });
    expect(done).toBeDisabled();

    await user.click(done);
    expect(onDone).not.toHaveBeenCalled();

    await user.click(screen.getByLabelText("I have saved these codes"));
    expect(done).toBeEnabled();
    await user.click(done);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("can be unticked again", async () => {
    const user = userEvent.setup();

    render(<RecoveryCodesView codes={CODES} onDone={vi.fn()} />);
    await user.click(screen.getByLabelText("I have saved these codes"));
    await user.click(screen.getByLabelText("I have saved these codes"));

    expect(screen.getByRole("button", { name: "Done" })).toBeDisabled();
  });

  it("copies them one to a line", async () => {
    const user = userEvent.setup();
    // After setup(): it installs a clipboard of its own, which this replaces.
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    render(<RecoveryCodesView codes={CODES} onDone={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Copy" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith("ABCDE-FGHJK\nMNPQR-STUVW"));
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("does not claim it copied when the clipboard is refused", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    render(<RecoveryCodesView codes={CODES} onDone={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Copy" }));

    await waitFor(() => expect(writeText).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Copied" })).not.toBeInTheDocument();
  });

  it("downloads them as a text file", async () => {
    const created: Blob[] = [];
    const createObjectURL = vi.fn((blob: Blob) => {
      created.push(blob);
      return "blob:codes";
    });
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const user = userEvent.setup();

    render(<RecoveryCodesView codes={CODES} onDone={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Download" }));

    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:codes");
    expect(created[0].type).toBe("text/plain");
    expect(await created[0].text()).toBe("ABCDE-FGHJK\nMNPQR-STUVW\n");
  });
});

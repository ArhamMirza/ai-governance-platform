import { afterEach, describe, expect, it } from "vitest";

import { showDialog } from "../src/dialog.ts";

afterEach(() => {
  document.documentElement.querySelectorAll("div").forEach((node) => {
    if (node.shadowRoot) node.remove();
  });
});

function dialogRoot(): ShadowRoot {
  const host = Array.from(document.documentElement.children).find(
    (node) => (node as HTMLElement).shadowRoot,
  ) as HTMLElement;
  return host.shadowRoot!;
}

const request = { toolName: "ChatGPT", rules: ["Payment card numbers", "Client names"] };

describe("a warning", () => {
  it("names the tool and the rules, and offers to go on or cancel", async () => {
    const result = showDialog(document, { ...request, mode: "warn" }, "open");
    const root = dialogRoot();

    expect(root.querySelector("h2")?.textContent).toBe("Check before you send");
    expect(root.textContent).toContain("ChatGPT is not cleared");
    expect(Array.from(root.querySelectorAll("li")).map((li) => li.textContent)).toEqual(request.rules);
    expect(Array.from(root.querySelectorAll("button")).map((b) => b.textContent)).toEqual([
      "Send anyway",
      "Cancel",
    ]);
    root.querySelector<HTMLButtonElement>("button.primary")!.click();
    await result;
  });

  it("resolves true only when the person chooses to send anyway", async () => {
    const result = showDialog(document, { ...request, mode: "warn" }, "open");

    Array.from(dialogRoot().querySelectorAll("button")).find((b) => b.textContent === "Send anyway")!.click();

    expect(await result).toBe(true);
  });

  it("resolves false on Cancel, and removes itself", async () => {
    const result = showDialog(document, { ...request, mode: "warn" }, "open");

    Array.from(dialogRoot().querySelectorAll("button")).find((b) => b.textContent === "Cancel")!.click();

    expect(await result).toBe(false);
    expect(Array.from(document.documentElement.children).some((n) => (n as HTMLElement).shadowRoot)).toBe(false);
  });

  it("treats Escape as not sending", async () => {
    const result = showDialog(document, { ...request, mode: "warn" }, "open");

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));

    expect(await result).toBe(false);
  });

  it("keeps the safe choice under the keyboard", async () => {
    const result = showDialog(document, { ...request, mode: "warn" }, "open");
    const cancel = Array.from(dialogRoot().querySelectorAll("button")).find((b) => b.textContent === "Cancel")!;

    expect(dialogRoot().activeElement).toBe(cancel);
    cancel.click();
    await result;
  });
});

describe("a refusal", () => {
  it("says it wasn't sent, and has no way to go on", async () => {
    const result = showDialog(document, { ...request, mode: "block" }, "open");
    const root = dialogRoot();

    expect(root.querySelector("h2")?.textContent).toBe("This was not sent");
    expect(Array.from(root.querySelectorAll("button")).map((b) => b.textContent)).toEqual(["OK"]);
    root.querySelector("button")!.click();
    expect(await result).toBe(false);
  });

  it("resolves false on Escape too", async () => {
    const result = showDialog(document, { ...request, mode: "block" }, "open");

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

    expect(await result).toBe(false);
  });
});

describe("the page cannot reach into it", () => {
  it("is built in a closed shadow root by default", async () => {
    const result = showDialog(document, { ...request, mode: "block" });
    const host = Array.from(document.documentElement.children).find(
      (node) => node.tagName === "DIV" && !node.id,
    ) as HTMLElement;

    expect(host.shadowRoot).toBeNull();
    expect(host.children).toHaveLength(0);
    expect(host.textContent).toBe("");
    // Dismiss it so the next test starts clean.
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await result;
  });

  it("writes rule names as text, never as markup", async () => {
    const result = showDialog(
      document,
      { toolName: "<img src=x onerror=alert(1)>", rules: ["<script>alert(1)</script>"], mode: "block" },
      "open",
    );
    const root = dialogRoot();

    expect(root.querySelector("img")).toBeNull();
    expect(root.querySelector("script")).toBeNull();
    expect(root.querySelector("li")?.textContent).toBe("<script>alert(1)</script>");
    root.querySelector("button")!.click();
    await result;
  });
});

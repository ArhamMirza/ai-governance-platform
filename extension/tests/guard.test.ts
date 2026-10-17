import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MAX_FILE_BYTES, installGuards, isTextFile } from "../src/guard.ts";
import type { Policy } from "../src/policy.ts";
import { CARD, makePolicy, ticketRule } from "./fixtures.ts";

const CLEAN = "Please summarise this article about gardening.";
const WARN_TEXT = "Notes on Project Falcon";
const MONITOR_TEXT = "see PROJ-1234 for details";

let uninstall: (() => void) | null = null;

afterEach(() => {
  uninstall?.();
  uninstall = null;
  document.body.innerHTML = "";
});

interface Setup {
  box: HTMLTextAreaElement;
  send: HTMLButtonElement;
  form: HTMLFormElement;
  report: ReturnType<typeof vi.fn>;
  confirm: ReturnType<typeof vi.fn>;
  replayDrop: ReturnType<typeof vi.fn>;
}

function setup(
  options: { policy?: Policy | null; host?: string; goOn?: boolean } = {},
): Setup {
  document.body.innerHTML = `
    <form id="chat">
      <textarea id="box"></textarea>
      <button type="submit" id="send" aria-label="Send message">Send</button>
    </form>
    <button id="other">Something else</button>`;
  const report = vi.fn();
  const confirm = vi.fn().mockResolvedValue(options.goOn ?? false);
  const replayDrop = vi.fn();
  const policy = options.policy === undefined ? makePolicy() : options.policy;
  uninstall = installGuards(document, {
    host: options.host ?? "chatgpt.com",
    getPolicy: () => policy,
    report,
    confirm,
    replayDrop,
  });
  return {
    box: document.getElementById("box") as HTMLTextAreaElement,
    send: document.getElementById("send") as HTMLButtonElement,
    form: document.getElementById("chat") as HTMLFormElement,
    report,
    confirm,
    replayDrop,
  };
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

function paste(target: Element, text: string): Event {
  const event = new Event("paste", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "clipboardData", { value: { getData: () => text } });
  target.dispatchEvent(event);
  return event;
}

function press(target: Element, key = "Enter", init: KeyboardEventInit = {}): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(event);
  return event;
}

function click(target: Element): MouseEvent {
  const event = new MouseEvent("click", { bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

function fakeFile(name: string, type: string, content: string, size = content.length): File {
  return { name, type, size, text: async () => content } as unknown as File;
}

function reportedRules(report: ReturnType<typeof vi.fn>): [number, string][] {
  return report.mock.calls.map(([match]) => [match.ruleId, match.action]);
}

describe("pasting", () => {
  it("stops a paste that a rule blocks, says why, and reports it", async () => {
    const { box, report, confirm } = setup();

    const event = paste(box, `my card is ${CARD}`);
    await settle();

    expect(event.defaultPrevented).toBe(true);
    expect(box.value).toBe("");
    expect(reportedRules(report)).toEqual([[1, "blocked"]]);
    expect(confirm).toHaveBeenCalledWith({
      mode: "block",
      toolName: "ChatGPT",
      rules: ["Payment card numbers"],
    });
  });

  it("holds a paste for a warning, and drops it if the person cancels", async () => {
    const { box, report, confirm } = setup({ goOn: false });

    const event = paste(box, WARN_TEXT);
    await settle();

    expect(event.defaultPrevented).toBe(true);
    expect(confirm).toHaveBeenCalledWith(expect.objectContaining({ mode: "warn", rules: ["Client names"] }));
    expect(box.value).toBe("");
    expect(reportedRules(report)).toEqual([[2, "warned"]]);
  });

  it("puts the text in once the person confirms, and records that they went on", async () => {
    const { box, report } = setup({ goOn: true });

    paste(box, WARN_TEXT);
    await settle();

    expect(box.value).toBe(WARN_TEXT);
    expect(reportedRules(report)).toEqual([[2, "overridden"]]);
  });

  it("lets a monitored paste through and counts it", async () => {
    const { box, report, confirm } = setup();

    const event = paste(box, MONITOR_TEXT);
    await settle();

    expect(event.defaultPrevented).toBe(false);
    expect(confirm).not.toHaveBeenCalled();
    expect(reportedRules(report)).toEqual([[3, "monitored"]]);
  });

  it("reports each rule that matched once, with the action taken", async () => {
    const { box, report } = setup();

    paste(box, `${WARN_TEXT} ${CARD} ${MONITOR_TEXT}`);
    await settle();

    expect(reportedRules(report)).toEqual([
      [1, "blocked"],
      [2, "blocked"],
      [3, "blocked"],
    ]);
  });

  it("leaves a clean paste completely alone", async () => {
    const { box, report, confirm } = setup();

    const event = paste(box, CLEAN);
    await settle();

    expect(event.defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
  });

  it("doesn't judge a paste of nothing but spaces, even for a rule that matches spaces", async () => {
    const spaces = makePolicy({
      rules: [{ ...ticketRule, id: 9, pattern: String.raw`\s{5}`, action: "block" }],
    });
    const { box, report } = setup({ policy: spaces });

    expect(paste(box, "     ").defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("ignores a paste with no text", async () => {
    const { box, report } = setup();

    expect(paste(box, "").defaultPrevented).toBe(false);
    expect(paste(box, "   ").defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("holds a tool the organization has approved only to what it isn't cleared for", async () => {
    const claude = setup({ host: "claude.ai" });
    expect(paste(claude.box, WARN_TEXT).defaultPrevented).toBe(false); // internal data is fine there
    expect(paste(claude.box, CARD).defaultPrevented).toBe(true); // confidential is not
    uninstall?.();

    const copilot = setup({ host: "copilot.microsoft.com" });
    expect(paste(copilot.box, CARD).defaultPrevented).toBe(false);
    expect(copilot.report).not.toHaveBeenCalled();
  });

  it("does nothing before the extension has a policy", async () => {
    const { box, report } = setup({ policy: null });

    expect(paste(box, CARD).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("does nothing on a site the platform doesn't know", async () => {
    const { box, report } = setup({ host: "example.com" });

    expect(paste(box, CARD).defaultPrevented).toBe(false);
    expect(paste(box, CARD).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("is not fooled by a lookalike site name", async () => {
    const { box, report } = setup({ host: "chatgpt.com.evil.net" });

    expect(paste(box, CARD).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("follows the policy as it changes", async () => {
    const policy = makePolicy();
    document.body.innerHTML = `<textarea id="box"></textarea>`;
    const box = document.getElementById("box")!;
    let current: Policy | null = policy;
    uninstall = installGuards(document, {
      host: "chatgpt.com",
      getPolicy: () => current,
      report: vi.fn(),
      confirm: vi.fn().mockResolvedValue(false),
    });

    expect(paste(box, CARD).defaultPrevented).toBe(true);
    current = makePolicy({ rules: [] });
    expect(paste(box, CARD).defaultPrevented).toBe(false);
    current = null;
    expect(paste(box, CARD).defaultPrevented).toBe(false);
  });
});

describe("sending with Enter", () => {
  it("stops Enter when the box holds something blocked", async () => {
    const { box, report } = setup();
    box.value = `card ${CARD}`;
    const site = vi.fn();
    box.addEventListener("keydown", site);

    const event = press(box);
    await settle();

    expect(event.defaultPrevented).toBe(true);
    expect(site).not.toHaveBeenCalled();
    expect(reportedRules(report)).toEqual([[1, "blocked"]]);
  });

  it("lets a clean message go", async () => {
    const { box, report } = setup();
    box.value = CLEAN;
    const site = vi.fn();
    box.addEventListener("keydown", site);

    const event = press(box);

    expect(event.defaultPrevented).toBe(false);
    expect(site).toHaveBeenCalledTimes(1);
    expect(report).not.toHaveBeenCalled();
  });

  it("ignores Enter on things that aren't a message box, even with sensitive text on them", async () => {
    const { report } = setup();
    document.body.insertAdjacentHTML("beforeend", `<div id="note">card ${CARD}</div><input id="pw" type="password" />`);
    (document.getElementById("pw") as HTMLInputElement).value = CARD;

    expect(press(document.getElementById("note")!).defaultPrevented).toBe(false);
    expect(press(document.getElementById("pw")!).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("ignores Shift+Enter, other keys and Enter outside a message box", async () => {
    const { box, other, report } = Object.assign(setup(), {
      other: document.getElementById("other") as HTMLElement,
    });
    box.value = CARD;

    expect(press(box, "Enter", { shiftKey: true }).defaultPrevented).toBe(false);
    expect(press(box, "a").defaultPrevented).toBe(false);
    expect(press(other, "Enter").defaultPrevented).toBe(false);
    expect(press(box, "Enter", { isComposing: true }).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("holds Enter for a warning and, on confirming, sends the key again", async () => {
    const { box, report } = setup({ goOn: true });
    box.value = WARN_TEXT;
    const site = vi.fn();
    box.addEventListener("keydown", site);

    const first = press(box);
    expect(first.defaultPrevented).toBe(true);
    await settle();

    expect(site).toHaveBeenCalledTimes(1);
    expect(site.mock.calls[0][0].key).toBe("Enter");
    expect(reportedRules(report)).toEqual([[2, "overridden"]]);
  });

  it("doesn't send it again when the person cancels", async () => {
    const { box } = setup({ goOn: false });
    box.value = WARN_TEXT;
    const site = vi.fn();
    box.addEventListener("keydown", site);

    press(box);
    await settle();

    expect(site).not.toHaveBeenCalled();
  });

  it("counts a monitored send once, even though Enter then submit both see it", async () => {
    const { box, form, report } = setup();
    box.value = MONITOR_TEXT;

    press(box);
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(reportedRules(report)).toEqual([[3, "monitored"]]);
  });

  it("judges what was pasted again when it is then sent", async () => {
    const { box, report } = setup();

    paste(box, MONITOR_TEXT);
    box.value = MONITOR_TEXT;
    press(box);

    expect(reportedRules(report)).toEqual([
      [3, "monitored"],
      [3, "monitored"],
    ]);
  });

  it("judges a different message afresh", async () => {
    const { box, report } = setup();
    box.value = MONITOR_TEXT;
    press(box);
    box.value = `${MONITOR_TEXT} and PROJ-9999`;

    press(box);

    expect(report).toHaveBeenCalledTimes(2);
  });

  it("judges the same message afresh once the moment has passed", async () => {
    vi.useFakeTimers();
    try {
      const { box, report } = setup();
      box.value = MONITOR_TEXT;
      press(box);
      vi.advanceTimersByTime(2500);

      press(box);

      expect(report).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("sending with a button or a form", () => {
  it("stops a click on the send button", async () => {
    const { box, send, report } = setup();
    box.value = `card ${CARD}`;
    const site = vi.fn();
    send.addEventListener("click", site);

    const event = click(send);
    await settle();

    expect(event.defaultPrevented).toBe(true);
    expect(site).not.toHaveBeenCalled();
    expect(reportedRules(report)).toEqual([[1, "blocked"]]);
  });

  it("recognises a send button by its label, not only its type", async () => {
    document.body.innerHTML = `<div><textarea id="box"></textarea><button id="go" aria-label="Send prompt" type="button">↑</button></div>`;
    const report = vi.fn();
    uninstall = installGuards(document, {
      host: "chatgpt.com",
      getPolicy: () => makePolicy(),
      report,
      confirm: vi.fn().mockResolvedValue(false),
    });
    const box = document.getElementById("box") as HTMLTextAreaElement;
    box.focus();
    box.value = CARD;

    expect(click(document.getElementById("go")!).defaultPrevented).toBe(true);
  });

  it.each([
    ["Submit prompt", "button"],
    ["Send", "button"],
    ["send-button", "button"],
  ])("recognises a send control labelled %s", async (label) => {
    const { box } = setup();
    box.focus();
    box.value = CARD;
    document.body.insertAdjacentHTML("beforeend", `<button type="button" id="go" aria-label="${label}">go</button>`);

    expect(click(document.getElementById("go")!).defaultPrevented).toBe(true);
  });

  it("doesn't take a button for a send control just because it is a button", async () => {
    const { box } = setup();
    box.focus();
    box.value = CARD;
    document.body.insertAdjacentHTML(
      "beforeend",
      `<button type="button" id="b1" aria-label="Resend invite">a</button><button type="button" id="b2" aria-label="Attach file">b</button>`,
    );

    expect(click(document.getElementById("b1")!).defaultPrevented).toBe(false);
    expect(click(document.getElementById("b2")!).defaultPrevented).toBe(false);
  });

  it("leaves other buttons alone", async () => {
    const { box, report } = setup();
    box.focus();
    box.value = CARD;

    expect(click(document.getElementById("other")!).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("clicks the button again once a warning is confirmed", async () => {
    const { box, send, report } = setup({ goOn: true });
    box.value = WARN_TEXT;
    const site = vi.fn((event: Event) => event.preventDefault());
    send.addEventListener("click", site);

    click(send);
    await settle();

    expect(site).toHaveBeenCalledTimes(1);
    expect(reportedRules(report)).toEqual([[2, "overridden"]]);
  });

  it("counts a typeless button inside a form as a send, since it submits the form", async () => {
    const { box, form } = setup();
    form.insertAdjacentHTML("beforeend", `<button id="plain">Go</button>`);
    box.value = CARD;

    expect(click(document.getElementById("plain")!).defaultPrevented).toBe(true);
  });

  it("doesn't take a button that submits nothing, even inside the form", async () => {
    const { box, form } = setup();
    form.insertAdjacentHTML("beforeend", `<button type="button" id="attach">Attach</button>`);
    box.value = CARD;

    expect(click(document.getElementById("attach")!).defaultPrevented).toBe(false);
  });

  it("does nothing for a send with nothing to send", async () => {
    const { send, report } = setup();

    expect(click(send).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });

  it("stops a form from submitting blocked text", async () => {
    const { box, form, report } = setup();
    box.value = CARD;

    const event = new Event("submit", { bubbles: true, cancelable: true });
    form.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(reportedRules(report)).toEqual([[1, "blocked"]]);
  });

  it("lets a clean form submit", async () => {
    const { box, form } = setup();
    box.value = CLEAN;

    const event = new Event("submit", { bubbles: true, cancelable: true });
    form.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
  });
});

describe("attached and dropped files", () => {
  function attach(files: File[]): { input: HTMLInputElement; site: ReturnType<typeof vi.fn> } {
    const input = document.createElement("input");
    input.type = "file";
    document.body.append(input);
    Object.defineProperty(input, "files", { value: files, configurable: true });
    Object.defineProperty(input, "value", { value: "C:\\fakepath\\notes.txt", writable: true });
    const site = vi.fn();
    input.addEventListener("change", site);
    return { input, site };
  }

  const change = (input: HTMLInputElement) =>
    input.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));

  it("holds back a text file with blocked content and clears the choice", async () => {
    const { report } = setup();
    const { input, site } = attach([fakeFile("export.csv", "text/csv", `name,card\nA,${CARD}`)]);

    change(input);
    await settle();

    expect(site).not.toHaveBeenCalled();
    expect(input.value).toBe("");
    expect(reportedRules(report)).toEqual([[1, "blocked"]]);
  });

  it("passes a clean text file on to the page, as if untouched", async () => {
    const { report } = setup();
    const { input, site } = attach([fakeFile("notes.txt", "text/plain", CLEAN)]);

    change(input);
    expect(site).not.toHaveBeenCalled(); // held while it is read
    await settle();

    expect(site).toHaveBeenCalledTimes(1);
    expect(input.value).not.toBe("");
    expect(report).not.toHaveBeenCalled();
  });

  it("recognises a text file by its extension when the type is missing", async () => {
    setup();
    const { input } = attach([fakeFile("settings.env", "", `KEY=${CARD}`)]);

    change(input);
    await settle();

    expect(input.value).toBe("");
  });

  it("asks before letting a file with warned content through, and does if told to", async () => {
    const { confirm } = setup({ goOn: true });
    const { input, site } = attach([fakeFile("brief.md", "text/markdown", WARN_TEXT)]);

    change(input);
    await settle();

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(site).toHaveBeenCalledTimes(1);
    expect(input.value).not.toBe("");
  });

  it("clears a file the person decides not to send", async () => {
    setup({ goOn: false });
    const { input, site } = attach([fakeFile("brief.md", "text/markdown", WARN_TEXT)]);

    change(input);
    await settle();

    expect(site).not.toHaveBeenCalled();
    expect(input.value).toBe("");
  });

  it("doesn't read files it can't, and the page sees them straight away", async () => {
    const { report } = setup();
    const pdf = attach([fakeFile("report.pdf", "application/pdf", CARD)]);
    const huge = attach([fakeFile("big.txt", "text/plain", CARD, MAX_FILE_BYTES + 1)]);

    change(pdf.input);
    change(huge.input);

    expect(pdf.site).toHaveBeenCalledTimes(1);
    expect(huge.site).toHaveBeenCalledTimes(1);
    expect(report).not.toHaveBeenCalled();
  });

  it("reads only the text files in a mixed selection", async () => {
    setup();
    // A picture whose bytes happen to look like a card number is not text to check.
    const { input, site } = attach([
      fakeFile("picture.png", "image/png", CARD),
      fakeFile("notes.txt", "text/plain", CLEAN),
    ]);

    change(input);
    await settle();

    expect(site).toHaveBeenCalledTimes(1);
    expect(input.value).not.toBe("");
  });

  it("checks the text files in a mixed selection", async () => {
    setup();
    const { input, site } = attach([
      fakeFile("picture.png", "image/png", "x"),
      fakeFile("cards.txt", "text/plain", CARD),
    ]);

    change(input);
    await settle();

    expect(site).not.toHaveBeenCalled();
    expect(input.value).toBe("");
  });

  it("leaves an unreadable file alone rather than blocking the upload", async () => {
    setup();
    const unreadable = { name: "a.txt", type: "text/plain", size: 5, text: async () => Promise.reject(new Error("no")) };
    const { input, site } = attach([unreadable as unknown as File]);

    change(input);
    await settle();

    expect(site).toHaveBeenCalledTimes(1);
  });

  function drop(files: File[], target: Element): Event {
    const event = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", { value: { files } });
    target.dispatchEvent(event);
    return event;
  }

  it("holds a dropped text file and drops it again only if it passes", async () => {
    const { replayDrop } = setup();
    const target = document.getElementById("other")!;
    const files = [fakeFile("notes.txt", "text/plain", CLEAN)];

    const event = drop(files, target);
    expect(event.defaultPrevented).toBe(true);
    expect(replayDrop).not.toHaveBeenCalled();
    await settle();

    expect(replayDrop).toHaveBeenCalledWith(target, files);
  });

  it("never replays a dropped file that is blocked", async () => {
    const { replayDrop, report } = setup();

    drop([fakeFile("cards.txt", "text/plain", CARD)], document.getElementById("other")!);
    await settle();

    expect(replayDrop).not.toHaveBeenCalled();
    expect(reportedRules(report)).toEqual([[1, "blocked"]]);
  });

  it("lets a dropped PDF straight through", async () => {
    const { replayDrop } = setup();

    const event = drop([fakeFile("a.pdf", "application/pdf", CARD)], document.getElementById("other")!);

    expect(event.defaultPrevented).toBe(false);
    expect(replayDrop).not.toHaveBeenCalled();
  });
});

describe("isTextFile", () => {
  it.each([
    [{ name: "a.txt", type: "text/plain", size: 10 }, true],
    [{ name: "a", type: "text/csv", size: 10 }, true],
    [{ name: "a.json", type: "application/json", size: 10 }, true],
    [{ name: "a.xml", type: "application/xml", size: 10 }, true],
    [{ name: "script.PY", type: "", size: 10 }, true],
    [{ name: "a.pdf", type: "application/pdf", size: 10 }, false],
    [{ name: "a.docx", type: "", size: 10 }, false],
    [{ name: "photo.png", type: "image/png", size: 10 }, false],
    [{ name: "noextension", type: "", size: 10 }, false],
    [{ name: "a.txt", type: "text/plain", size: MAX_FILE_BYTES + 1 }, false],
    [{ name: "a.txt", type: "text/plain", size: MAX_FILE_BYTES }, true],
  ])("%j", (file, expected) => {
    expect(isTextFile(file)).toBe(expected);
  });
});

describe("what leaves the page", () => {
  it("reports only a rule's number and what happened -- never the text", async () => {
    const { box, report } = setup({ goOn: true });

    paste(box, `${CARD} ${WARN_TEXT}`);
    await settle();
    box.value = `${CARD} ${WARN_TEXT}`;
    press(box);
    await settle();

    expect(report.mock.calls.length).toBeGreaterThan(0);
    for (const [match] of report.mock.calls) {
      expect(Object.keys(match).sort()).toEqual(["action", "ruleId"]);
    }
    expect(JSON.stringify(report.mock.calls)).not.toContain(CARD);
    expect(JSON.stringify(report.mock.calls)).not.toContain("Falcon");
  });

  it("tells the person which rules matched, never what matched", async () => {
    const { box, confirm } = setup();

    paste(box, `${CARD} ${WARN_TEXT}`);
    await settle();

    expect(JSON.stringify(confirm.mock.calls)).not.toContain(CARD);
    expect(JSON.stringify(confirm.mock.calls)).not.toContain("Falcon");
  });

  it("stops watching once uninstalled", async () => {
    const { box, report } = setup();
    uninstall?.();
    uninstall = null;

    expect(paste(box, CARD).defaultPrevented).toBe(false);
    expect(report).not.toHaveBeenCalled();
  });
});

beforeEach(() => {
  document.body.innerHTML = "";
});

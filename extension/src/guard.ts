/**
 * Checks what goes into an AI chat, on the page it is typed into.
 *
 * Installed by the content script on catalogued AI sites only. It watches the
 * ways text leaves the box -- a paste, Enter, a send button, a form submit, an
 * attached or dropped text file -- scans it with the organization's rules, and
 * either lets it through, asks the person to confirm, or stops it. The text is
 * read and judged here and goes nowhere: all that is reported is which rule
 * matched and what happened.
 *
 * Everything the browser provides arrives through `GuardDeps`, so this file
 * is tested in jsdom without a browser, and the same code runs for real.
 *
 * This is best effort by nature. Chat sites are free to rebuild their pages,
 * so the send-button and Enter handling can need updating when one does; a
 * paste and a form submit are standard events and hold up better. Files that
 * aren't plain text (PDFs, Office documents, images) are not read.
 */

import type { UsageAction } from "./events.ts";
import { decide, type Decision } from "./decide.ts";
import type { Policy } from "./policy.ts";

export interface ReportedMatch {
  ruleId: number;
  action: UsageAction;
}

export interface ConfirmRequest {
  mode: "warn" | "block";
  toolName: string;
  /** The names of the rules that matched -- never what matched. */
  rules: string[];
}

export interface GuardDeps {
  host: string;
  getPolicy(): Policy | null;
  report(match: ReportedMatch): void;
  /** Shows the person a warning (they may go on) or a refusal (they may not). */
  confirm(request: ConfirmRequest): Promise<boolean>;
  /** Puts a dropped set of files back in play after they have passed. */
  replayDrop?(target: EventTarget, files: File[]): void;
}

/** Files bigger than this aren't read: a page stalling on a huge upload is worse than the gap. */
export const MAX_FILE_BYTES = 1_000_000;

const TEXT_EXTENSIONS = new Set([
  "txt", "md", "markdown", "csv", "tsv", "json", "jsonl", "xml", "yaml", "yml", "toml", "ini",
  "log", "html", "htm", "css", "sql", "py", "js", "ts", "tsx", "jsx", "java", "c", "cc", "cpp",
  "h", "cs", "go", "rs", "rb", "php", "sh", "ps1", "bat", "env", "conf", "cfg", "properties",
]);

/** Whether a file is plain text we can read and check. */
export function isTextFile(file: Pick<File, "name" | "type" | "size">): boolean {
  if (file.size > MAX_FILE_BYTES) return false;
  if (file.type.startsWith("text/")) return true;
  if (file.type === "application/json" || file.type === "application/xml") return true;
  const extension = file.name.includes(".") ? file.name.split(".").pop()!.toLowerCase() : "";
  return TEXT_EXTENSIONS.has(extension);
}

/** How long a message that has just been judged is remembered, so the same
 * send isn't judged again by the next handler it passes through. */
const APPROVAL_MS = 2000;

function isComposer(element: Element | null): element is HTMLElement {
  if (!(element instanceof HTMLElement)) return false;
  if (element instanceof HTMLTextAreaElement) return true;
  if (element instanceof HTMLInputElement) {
    return ["text", "search", ""].includes(element.type.toLowerCase());
  }
  return element.isContentEditable || element.getAttribute("role") === "textbox";
}

function composerText(element: HTMLElement): string {
  if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
    return element.value;
  }
  return element.innerText || element.textContent || "";
}

const SEND_LABEL = /\b(send|submit)\b/i;

function isSendControl(element: Element): boolean {
  // A button with no type attribute is a "submit" button, but it only submits
  // anything if it is inside a form; outside one it is just a button.
  const submits =
    (element instanceof HTMLInputElement || element instanceof HTMLButtonElement) &&
    element.type === "submit" &&
    element.form !== null;
  if (submits) return true;
  const label = [
    element.getAttribute("aria-label"),
    element.getAttribute("title"),
    element.getAttribute("data-testid"),
  ]
    .filter(Boolean)
    .join(" ");
  return SEND_LABEL.test(label);
}

export function installGuards(doc: Document, deps: GuardDeps): () => void {
  let replaying = false;
  let approved: { text: string; until: number } | null = null;
  let lastComposer: HTMLElement | null = null;

  const now = () => Date.now();

  function decisionFor(text: string): Decision | null {
    const policy = deps.getPolicy();
    if (policy === null || text.trim() === "") return null;
    const decision = decide(text, deps.host, policy);
    return decision && decision.action !== null ? decision : null;
  }

  function record(decision: Decision, action: UsageAction): void {
    for (const hit of decision.hits) deps.report({ ruleId: hit.rule.id, action });
  }

  function remember(text: string): void {
    approved = { text, until: now() + APPROVAL_MS };
  }

  function isApproved(text: string): boolean {
    return approved !== null && approved.text === text && approved.until > now();
  }

  /**
   * Judges `text`. Returns "passed" when nothing needs stopping (the caller
   * carries on), or "held" when it has been stopped or is waiting on the
   * person; `resume` is then called if they go ahead, `cancel` if they don't.
   */
  function gate(text: string, resume: () => void, cancel?: () => void): "passed" | "held" {
    const decision = decisionFor(text);
    if (decision === null || isApproved(text)) return "passed";
    const request = {
      toolName: decision.toolName,
      rules: decision.hits.map((hit) => hit.rule.name),
    };

    if (decision.action === "monitor") {
      record(decision, "monitored");
      remember(text);
      return "passed";
    }
    if (decision.action === "block") {
      record(decision, "blocked");
      void deps.confirm({ mode: "block", ...request });
      cancel?.();
      return "held";
    }
    void deps.confirm({ mode: "warn", ...request }).then((goOn) => {
      if (goOn) {
        record(decision, "overridden");
        remember(text);
        replaying = true;
        try {
          resume();
        } finally {
          replaying = false;
        }
      } else {
        record(decision, "warned");
        cancel?.();
      }
    });
    return "held";
  }

  function stop(event: Event): void {
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function composerFor(from: Element | null): HTMLElement | null {
    if (isComposer(from)) return from;
    const scope = from?.closest("form") ?? null;
    const inForm = scope?.querySelector<HTMLElement>("textarea, [contenteditable='true'], [role='textbox']");
    if (inForm) return inForm;
    if (isComposer(doc.activeElement)) return doc.activeElement;
    return lastComposer;
  }

  // ---------- paste ----------

  function insertText(target: Element | null, text: string): void {
    const element = composerFor(target);
    if (element === null) return;
    element.focus();
    let done = false;
    try {
      done = doc.execCommand("insertText", false, text);
    } catch {
      done = false;
    }
    if (done) return;
    if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
      const start = element.selectionStart ?? element.value.length;
      const end = element.selectionEnd ?? element.value.length;
      element.setRangeText(text, start, end, "end");
    } else {
      element.append(doc.createTextNode(text));
    }
    element.dispatchEvent(new Event("input", { bubbles: true }));
  }

  const onPaste = (event: ClipboardEvent) => {
    const text = event.clipboardData?.getData("text/plain") ?? "";
    const target = event.target instanceof Element ? event.target : null;
    // A paste isn't a send: it is judged on its own, then forgotten, so the
    // person can send what they pasted and have that judged separately.
    const verdict = gate(text, () => insertText(target, text));
    if (verdict === "held") stop(event);
    approved = null;
  };

  // ---------- sending ----------

  const onKeyDown = (event: KeyboardEvent) => {
    if (replaying || event.key !== "Enter" || event.shiftKey || event.altKey || event.isComposing) return;
    const target = event.target instanceof Element ? event.target : null;
    if (!isComposer(target)) return;
    const verdict = gate(composerText(target), () => {
      target.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true, cancelable: true }),
      );
    });
    if (verdict === "held") stop(event);
  };

  const onClick = (event: MouseEvent) => {
    if (replaying || !(event.target instanceof Element)) return;
    const control = event.target.closest("button, [role='button'], input[type='submit']");
    if (control === null || !isSendControl(control)) return;
    const composer = composerFor(control);
    if (composer === null) return;
    const verdict = gate(composerText(composer), () => (control as HTMLElement).click());
    if (verdict === "held") stop(event);
  };

  const onSubmit = (event: SubmitEvent) => {
    if (replaying || !(event.target instanceof HTMLFormElement)) return;
    const form = event.target;
    const text = Array.from(
      form.querySelectorAll<HTMLElement>("textarea, input[type='text'], input[type='search'], [contenteditable='true'], [role='textbox']"),
    )
      .map(composerText)
      .join("\n");
    const verdict = gate(text, () => form.requestSubmit());
    if (verdict === "held") stop(event);
  };

  const onFocus = (event: FocusEvent) => {
    if (isComposer(event.target instanceof Element ? event.target : null)) {
      lastComposer = event.target as HTMLElement;
    }
  };

  // ---------- files ----------

  async function readText(files: File[]): Promise<string> {
    const parts: string[] = [];
    for (const file of files) {
      if (!isTextFile(file)) continue;
      try {
        parts.push(await file.text());
      } catch {
        // An unreadable file is left alone rather than blocking the upload.
      }
    }
    return parts.join("\n");
  }

  const onChange = (event: Event) => {
    if (replaying) return;
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== "file") return;
    const files = Array.from(input.files ?? []);
    if (!files.some(isTextFile)) return;
    stop(event);
    void readText(files).then((text) => {
      const replay = () => {
        replaying = true;
        try {
          input.dispatchEvent(new Event("change", { bubbles: true }));
        } finally {
          replaying = false;
        }
      };
      if (gate(text, replay, () => (input.value = "")) === "passed") replay();
    });
  };

  const onDrop = (event: DragEvent) => {
    if (replaying) return;
    // Taken now: a drop's files can't be read once the event has finished.
    const files = Array.from(event.dataTransfer?.files ?? []);
    if (!files.some(isTextFile) || event.target === null) return;
    const target = event.target;
    stop(event);
    void readText(files).then((text) => {
      const replay = () => {
        replaying = true;
        try {
          deps.replayDrop?.(target, files);
        } finally {
          replaying = false;
        }
      };
      if (gate(text, replay) === "passed") replay();
    });
  };

  doc.addEventListener("paste", onPaste, true);
  doc.addEventListener("keydown", onKeyDown, true);
  doc.addEventListener("click", onClick, true);
  doc.addEventListener("submit", onSubmit, true);
  doc.addEventListener("focusin", onFocus, true);
  doc.addEventListener("change", onChange, true);
  doc.addEventListener("drop", onDrop, true);

  return () => {
    doc.removeEventListener("paste", onPaste, true);
    doc.removeEventListener("keydown", onKeyDown, true);
    doc.removeEventListener("click", onClick, true);
    doc.removeEventListener("submit", onSubmit, true);
    doc.removeEventListener("focusin", onFocus, true);
    doc.removeEventListener("change", onChange, true);
    doc.removeEventListener("drop", onDrop, true);
  };
}

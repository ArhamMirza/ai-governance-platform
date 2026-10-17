/**
 * The box shown when text is stopped or needs a second look.
 *
 * Built inside a closed shadow root so the AI site's own styles and scripts
 * can't restyle it, read it or click it for the person. It names the rules
 * that matched and nothing that was matched: showing the text back would put
 * the sensitive data on screen again for no benefit.
 */

import type { ConfirmRequest } from "./guard.ts";

const STYLE = `
  :host { all: initial; }
  .backdrop {
    position: fixed; inset: 0; z-index: 2147483647;
    display: flex; align-items: center; justify-content: center;
    background: rgba(15, 23, 42, 0.55);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .box {
    box-sizing: border-box; width: min(440px, calc(100vw - 32px));
    padding: 22px 24px; border-radius: 10px;
    background: #ffffff; color: #0f172a;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
  }
  h2 { margin: 0 0 8px; font-size: 18px; line-height: 1.3; }
  p { margin: 0 0 10px; font-size: 14px; line-height: 1.5; }
  ul { margin: 0 0 12px; padding-left: 20px; font-size: 14px; }
  .actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
  button {
    font: inherit; font-size: 14px; padding: 8px 16px; border-radius: 6px;
    border: 1px solid #94a3b8; background: #ffffff; color: #0f172a; cursor: pointer;
  }
  button.primary { background: #1d4ed8; border-color: #1d4ed8; color: #ffffff; }
  button:focus-visible { outline: 3px solid #93c5fd; outline-offset: 2px; }
`;

function element<K extends keyof HTMLElementTagNameMap>(
  doc: Document,
  tag: K,
  text?: string,
  className?: string,
): HTMLElementTagNameMap[K] {
  const node = doc.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

/**
 * Shows the dialog and resolves when it is dismissed. Resolves true only when
 * the person chose to go ahead, which only a warning offers; a refusal always
 * resolves false.
 */
export function showDialog(
  doc: Document,
  request: ConfirmRequest,
  // Closed in the browser, so the page can't reach in; tests open it to look.
  shadowMode: ShadowRootMode = "closed",
): Promise<boolean> {
  return new Promise((resolve) => {
    const host = doc.createElement("div");
    const root = host.attachShadow({ mode: shadowMode });
    const style = doc.createElement("style");
    style.textContent = STYLE;

    const backdrop = element(doc, "div", undefined, "backdrop");
    const box = element(doc, "div", undefined, "box");
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-modal", "true");
    const blocking = request.mode === "block";
    const title = element(doc, "h2", blocking ? "This was not sent" : "Check before you send");
    title.id = "ai-governance-title";
    box.setAttribute("aria-labelledby", title.id);

    box.append(
      title,
      element(
        doc,
        "p",
        blocking
          ? `${request.toolName} is not cleared for this kind of information, so it was stopped:`
          : `${request.toolName} is not cleared for this kind of information. This looks like it contains:`,
      ),
    );
    const list = element(doc, "ul");
    for (const name of request.rules) list.append(element(doc, "li", name));
    box.append(list);
    box.append(
      element(
        doc,
        "p",
        blocking
          ? "Remove it and try again. If you think this is a mistake, tell the governance team."
          : "If you go on, that is recorded as a count. The text itself is not.",
      ),
    );

    const actions = element(doc, "div", undefined, "actions");
    let focusTarget: HTMLButtonElement;

    const close = (goOn: boolean) => {
      doc.removeEventListener("keydown", onKey, true);
      host.remove();
      resolve(goOn);
    };

    if (blocking) {
      const ok = element(doc, "button", "OK", "primary");
      ok.addEventListener("click", () => close(false));
      actions.append(ok);
      focusTarget = ok;
    } else {
      const cancel = element(doc, "button", "Cancel", "primary");
      const goOn = element(doc, "button", "Send anyway");
      cancel.addEventListener("click", () => close(false));
      goOn.addEventListener("click", () => close(true));
      actions.append(goOn, cancel);
      // The safe choice is the one under the keyboard's hand.
      focusTarget = cancel;
    }
    box.append(actions);
    backdrop.append(box);
    root.append(style, backdrop);

    // Escape always means "do not send".
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopImmediatePropagation();
        close(false);
      }
    }
    doc.addEventListener("keydown", onKey, true);

    doc.documentElement.append(host);
    focusTarget.focus();
  });
}

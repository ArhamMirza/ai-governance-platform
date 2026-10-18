// Applied before the first paint, so a pinned theme never shows a frame
// of the other one. Mirrors src/shared/theme.ts -- "system" is the
// absence of the attribute, and unreadable storage means "follow the OS".
//
// A file of its own, not an inline script in index.html, so the page can be
// served with a Content-Security-Policy that allows scripts from its own
// origin only (see deploy/).
try {
  var t = localStorage.getItem("governance.theme");
  if (t === "light" || t === "dark") {
    document.documentElement.setAttribute("data-theme", t);
  }
} catch {
  /* private window or blocked site data: fall back to the OS setting */
}

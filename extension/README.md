# AI Governance browser extension

Applies the organization's AI-use policy inside **Chrome and Edge**. It is the
part of the platform that acts on an employee's machine: the platform decides
which AI tools are approved and what must not be typed into them; this carries
it out.

What it does, on the AI sites the platform has catalogued:

- **Unapproved site** — counts the visit, warns first, or blocks it, as the
  platform's *AI use settings* say (**block is the default**). The page it shows
  offers **Request this tool**, which opens the employee portal with the tool
  filled in; in warn mode it also offers **Continue anyway** for an hour.
- **What goes in** — checks text that is pasted, sent (Enter, a send button, a
  form) or attached/dropped as a plain-text file against the **data rules**.
  A rule can *monitor* (count it), *warn* (the person confirms or cancels) or
  *block* (new rules start on *block*). A tool approved for a class of data isn't held to rules about that
  class or lower.
- **Reports counts** — one number per day, site, kind of event, rule and
  action. Nothing else.

## What it never does

- It never sends what you type, paste or attach. The text is read and judged
  on the computer; only "rule 4 matched, the person cancelled" leaves it.
- It never records a URL, a page title or the time of day, and only reports
  sites in the platform's AI tool catalogue (the platform refuses any other).
- It runs its checking script **only** on catalogued AI domains.

## What has been tested

- **Unit tests** (`npm test`) cover the decision logic, the policy handling, the
  counting, the platform communication, the interception of pastes, sends and
  uploads, and the dialog.
- **A real-browser test** (`e2e/`) loads the built extension into **real Chrome
  and real Edge** against a running platform and drives it with a real keyboard
  and mouse: 51 checks pass in each. See [e2e/README.md](e2e/README.md).
- **Not tested here:** force-install by enterprise policy and managed storage
  (they need a managed machine), Chrome Web Store / Edge Add-ons packaging, or
  any real AI site: the test uses a stand-in chat page, so it shows the
  mechanics work, not that a particular AI site's page is handled. Run the test
  script below on your own setup before a rollout.

## Read this before rolling it out

**It only covers browsers it is installed in.** The extension is installed per
browser *profile*, and it only runs in private windows if that is allowed for it
(force-installing it and disabling private windows closes both gaps). It does not see other
browsers, desktop apps (the ChatGPT app, Copilot inside Office), mobile, or API
and command-line use. IT must block other browsers if that matters to you.

**A person can remove it unless it is force-installed by policy.** Treat
force-installation as required, not optional (see below).

**The DLP is pattern matching on text.** It catches card numbers, bank and
national IDs, keys and tokens, passwords written out, and your own keyword
lists and patterns. It does not understand meaning: a paraphrased or
spelled-out secret passes, and some innocent text will match. It reduces
accidents; it isn't a guarantee.

**Files:** plain-text files up to 1 MB (`.txt`, `.csv`, `.json`, `.md`, source
code and similar) are read and checked. PDFs, Word/Excel files, images and
anything larger **pass through unchecked**.

**It depends on the AI sites' pages.** Pasting, form submission and most
send buttons are standard browser events and hold up well. Sites rebuild their
pages without notice, so Enter-to-send and send-button detection can need
updating when one does. The code that does it is `src/guard.ts`.

**Resumed sends are replayed, not original.** When a warning is confirmed (or
a clean file is held while it is read), the extension re-sends the key press,
click or drop on the person's behalf. Browsers mark such events as not
"trusted"; a site that insists on trusted events will ignore the replay, and
the person has to press send again. Where a site does that, tell us and the
handling for that site can be adjusted.

**Broad browser permission.** The manifest asks for access to all sites
(`<all_urls>`). The browser requires it to redirect any catalogued domain to
the "not approved" page. The checking script is registered only for the
catalogued domains, and the code reads and reports nothing from any other page.
You can verify that in `src/background.ts`, `src/rules.ts` and `src/guard.ts`.

**Counts are advisory, not forensic.** One key is shared by all browsers, so
anyone who obtained it could send false counts. Don't treat them as evidence
against an individual.

**Tell your staff.** Monitoring employees without notice, consultation or a
lawful basis is unlawful in many places. The platform's *AI use settings* page
holds the notice employees read on their AI tools page; write it plainly. This
README isn't legal advice.

## Build

Needs Node 22+.

```bash
cd extension
npm ci
npm test         # unit tests
npm run build    # type-checks, then bundles into dist/
```

`dist/` is the extension. `npm run lint` runs oxlint.

## Try it on one machine (unpacked)

The simplest way, on your own laptop with no system policy changes:

1. Run the platform locally and create an enrollment key (**AI Tools →
   Settings → Create Key**).
2. Build a **development** extension, which reads its settings from its own
   storage: `DEV_CONFIG=1 npm run build`. (Never deploy this build; production
   builds don't read that setting.)
3. Chrome: open `chrome://extensions`, switch on **Developer mode**, **Load
   unpacked**, choose `dist/`. Edge: the same at `edge://extensions`. To try it in a
   private window, open the extension's **Details** and turn on **Allow in Incognito**
   (it is off by default, which is why a real rollout disables private windows).
4. Click **service worker** on the extension's card to open its console and run:

   ```js
   chrome.storage.local.set({ devConfig: {
     serverUrl: "http://localhost:8000",
     portalUrl: "http://localhost:5173",
     enrollmentKey: "aigk_..."          // the key from step 1
   } })
   ```

   The icon's `!` badge clears within a few seconds once it has fetched a policy.

To try it the way a deployment works, with the real managed policy instead:
build normally (`npm run build`), load `dist/`, and give the browser the
settings through its enterprise policy. On Windows, with an elevated PowerShell:

```powershell
$id = "<the extension ID>"
# Chrome
$key = "HKLM:\SOFTWARE\Policies\Google\Chrome\3rdparty\extensions\$id\policy"
# Edge:  "HKLM:\SOFTWARE\Policies\Microsoft\Edge\3rdparty\extensions\$id\policy"
New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name serverUrl     -Value "http://localhost:8000"
Set-ItemProperty -Path $key -Name portalUrl     -Value "http://localhost:5173"
Set-ItemProperty -Path $key -Name enrollmentKey -Value "<key from the platform>"
```

On macOS/Linux put the same three values in a JSON file in the browser's
managed-policy folder, e.g. `/etc/opt/chrome/policies/managed/ai.json`:

```json
{ "3rdparty": { "extensions": { "<extension ID>": {
    "serverUrl": "https://governance.example.com",
    "portalUrl": "https://portal.example.com",
    "enrollmentKey": "aigk_..." } } } }
```

Plain `http` is accepted for `localhost` only. Restart the browser, or open
`chrome://policy` and **Reload policies**, and check the values appear. The
extension ID is shown on its card in `chrome://extensions`.

## Test script (once in Chrome, once in Edge)

With the extension connected and a seeded or real platform:

1. **Policy arrives.** Click the toolbar icon: it says *Connected*. The `!`
   badge is gone.
2. **Unapproved site.** In AI use settings choose *Block*, wait up to 15
   minutes (or restart the browser), then open an unapproved site from the
   catalogue (e.g. `grok.com`). You should land on the *not approved* page.
   *Request this tool* opens the portal's request form with the tool filled in.
3. **Warn.** Choose *Warn*, reload policy, open the same site: you get the
   page with **Continue anyway**; it opens the site and doesn't ask again for an
   hour.
4. **Approved site, clean text.** Open an approved tool; paste ordinary text:
   nothing happens.
5. **Block.** On an unapproved site, paste a test card number
   (`4111 1111 1111 1111`): the paste is refused and a box names the rule.
   Type one and press Enter, or click send: also refused.
6. **Warn rule.** Set a rule to *warn* (rules start on *block*), then paste text
   matching it: a box offers **Cancel** or **Send anyway**. Both are counted
   (*warned* / *overridden*). A *block* rule has no **Send anyway**.
7. **Approval honoured.** The same card number into a tool approved for
   confidential data: allowed.
8. **Files.** Attach a `.txt` with a test card number: refused. Attach a clean
   `.txt`: goes through. Attach a PDF: goes through unchecked (as documented).
9. **Counts.** Within ~5 minutes the platform's **Usage** page shows the
   counts for you — and no text. The same page's **Who has the extension**
   section lists you as reporting (or, if the browser profile's address matches
   no account, counts you as a reporter that matches nobody). The extension
   checks in once a day.
10. **Outage.** Stop the platform; sites keep following the last policy.

## Roll it out to everyone

### 1. Get a stable extension ID

An unpacked extension gets a random ID. Policy needs a fixed one, so sign it
with a key you keep safe:

```bash
openssl genrsa -out key.pem 2048              # keep this secret and backed up
openssl rsa -in key.pem -pubout -outform DER | openssl base64 -A   # the public key
```

Build with that public key embedded and note the ID it prints:

```bash
EXTENSION_PUBLIC_KEY="<the public key>" npm run build
```

### 2. Choose how it is delivered

**A. A store listing (simplest; updates itself).** Zip `dist/` and upload it as
an **unlisted** item to the Chrome Web Store and/or Microsoft Edge Add-ons
(each needs a developer account). Use the ID the store gives you.
Update URL: Chrome `https://clients2.google.com/service/update2/crx`, Edge
`https://edge.microsoft.com/extensionwebstorebase/v1/crx`.

**B. Self-hosted (stays in-house).** Pack it with your key:

```bash
chrome --pack-extension=dist --pack-extension-key=key.pem   # makes dist.crx
```

Host the `.crx` and an update manifest on an HTTPS address you control:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">
  <app appid="EXTENSION_ID">
    <updatecheck codebase="https://tools.example.com/ai-governance-0.1.0.crx" version="0.1.0" />
  </app>
</gupdate>
```

Chrome and Edge only install extensions from outside their stores on
**managed** machines (domain-joined, or enrolled in your device management);
on unmanaged Windows machines they refuse.

### 3. Force-install and configure it

Set these by Group Policy (ADMX templates), Intune settings catalog /
custom OMA-URI, or Google Admin. Replace `EXTENSION_ID` and the update URL.

**Chrome** — policy `ExtensionSettings`:

```json
{ "EXTENSION_ID": {
    "installation_mode": "force_installed",
    "update_url": "https://clients2.google.com/service/update2/crx",
    "toolbar_pin": "force_pinned" } }
```

**Edge** — the same policy name, with Edge's update URL:

```json
{ "EXTENSION_ID": {
    "installation_mode": "force_installed",
    "update_url": "https://edge.microsoft.com/extensionwebstorebase/v1/crx",
    "toolbar_pin": "force_pinned" } }
```

(For a self-hosted file, use your `update.xml` address as `update_url`.)

**The extension's own settings** — the third-party policy for that ID, in each
browser (`Google\Chrome\3rdparty\extensions` / `Microsoft\Edge\3rdparty\extensions`,
or the same JSON shape in Intune/Admin):

```json
{ "serverUrl": "https://governance.example.com",
  "portalUrl": "https://portal.example.com",
  "enrollmentKey": "aigk_..." }
```

### 4. Close the easy ways round it

- Block or remove other browsers on managed machines.
- Disable private windows (`IncognitoModeAvailability = 1` in Chrome,
  `InPrivateModeAvailability = 1` in Edge), or the extension can be bypassed there.
- Turn off extension developer mode (`ExtensionDeveloperModeSettings = 1`).
- Sign the browser profile in with the work account (Chrome `BrowserSignin`,
  Edge `BrowserSignin` / Entra SSO) so counts carry the employee's email.
  Without it they are filed under `unidentified@browser.invalid`.

### 5. Rotating the key

On the platform: **AI Tools → Settings → Replace Key**. The old key stops
working at once; update the `enrollmentKey` policy and browsers pick it up
without a restart.

## How it behaves when things go wrong

| Situation | What it does |
| --- | --- |
| Never connected (no policy yet) | Does nothing; the icon shows `!`. Nothing is blocked or scanned. |
| Platform unreachable, or the key is refused | Keeps enforcing the **last good policy**. Never loosens. Shows `!`. |
| Counts can't be sent | Keeps them and retries every 5 minutes. |
| Platform refuses a batch outright | Drops that batch (retrying would never work). |
| Open tabs when the policy changes | New rules apply to pages loaded afterwards. |

## Layout

| Path | What it is |
| --- | --- |
| `src/policy.ts`, `decide.ts`, `rules.ts` | Pure logic: which tool a host is, what to do with text, the browser rules. |
| `src/events.ts`, `sync.ts`, `config.ts` | Counting, talking to the platform, managed settings. |
| `src/guard.ts`, `dialog.ts`, `content.ts` | The checking on the page. |
| `src/background.ts` | The service worker that ties it together. |
| `src/blocked.ts`, `popup.ts`, `messages.ts`, `public/` | The *not approved* page, the toolbar popup, and the messages between pages and the service worker. |
| `src/configSource.ts` | Where settings come from: managed policy only, plus a development-only override. |
| `e2e/` | The real-browser test (Chrome and Edge). |
| `../frontend/src/shared/dlp/detectors.ts` | The rule engine, shared with the platform's rule tester so both agree. |

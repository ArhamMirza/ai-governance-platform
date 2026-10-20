# Real-browser test

Loads the **built extension into a real Chrome or Edge**, points it at a
**running platform**, and drives it: the policy arrives, unapproved sites are
redirected, pastes and sends are stopped or warned about, counts reach the
platform, and a refused key leaves the last good policy in force. It covers
what the unit tests can't: the manifest, the service worker, the browser's
redirect and script-registration APIs, and a real keyboard and mouse.

It is run by hand and is not part of CI (it needs a browser and a running
platform).

## What it checks (49 checks)

- starts unconfigured and shows the `!` badge; connects and clears it
- fetches the policy with the enrollment key; installs one redirect rule for
  each unapproved domain; registers the checking script on catalogued domains only
- *warn* mode: an unapproved site becomes the extension's page, names the tool,
  links to the portal's request form, and **Continue anyway** lets it through
- *block* mode: no way to continue; *monitor* mode: nothing is redirected
- a clean message is sent; internal data goes to a tool cleared for it; a card
  number is refused on Enter and on the send button, with a dialog; a rule about
  more sensitive data than the tool is cleared for raises a warning, where
  **Cancel** keeps it unsent and **Send anyway** sends it
- the counts waiting to be sent contain no text from the page, only the allowed
  fields; they reach the platform's Usage page and the buffer empties; the browser
  also checks in once a day, with no counts, so the platform can show who is covered
- a refused key is reported, the last good policy stays in force, the badge returns

## Run it

You need Node 22+, Chrome and/or Edge, and `openssl` on the path (to make a
throwaway certificate: some AI domains are on the browser's HTTPS-only list).

1. **Start the platform with demo data**

   ```bash
   cd backend
   alembic upgrade head
   python -m app.seed
   uvicorn app.main:app --port 8000
   ```

2. **Have an account that is the Chief AI Governance Officer.** Register an
   admin account on the platform, then assign it the *Chief AI Governance
   Officer* role on the Governance Roles page. (The test signs in as it to create
   the enrollment key and change the unapproved-site setting. It leaves the
   platform's setting on *monitor* when it finishes.)

3. **Build the development extension and install the test's dependency**

   ```bash
   cd extension
   DEV_CONFIG=1 npm run build        # a DEV build: reads its settings from its own storage
   cd e2e
   npm install
   ```

   On Windows PowerShell: `$env:DEV_CONFIG = "1"; npm run build`.

4. **Run**

   ```bash
   E2E_EMAIL=you@example.com E2E_PASSWORD=... npm run test:chrome
   E2E_EMAIL=you@example.com E2E_PASSWORD=... npm run test:edge
   ```

   (PowerShell: set `$env:E2E_EMAIL` and `$env:E2E_PASSWORD` first.)

Screenshots of the blocked pages and dialogs are saved in `shots/`.

Optional: `PLATFORM_URL` (default `http://localhost:8000`), `BROWSER_EXE` (the
browser's path if it isn't found), `EXTENSION_DIR` (default `../dist`).

## Notes

- **Use a throwaway platform database.** The test creates an enrollment key,
  switches the unapproved-site setting, and adds usage counts.
- The test **refuses to run against a production build**: it needs the DEV
  build's settings override. The DEV build is for testing only and must never
  be deployed; production builds don't read that setting.
- The browser runs headless with its own empty profile and a throwaway
  certificate, and `*.chatgpt.com`, `claude.ai`, `grok.com` and a few other AI
  domains are mapped to this machine for the test only.
- On Edge the test starts the browser itself and attaches to it (Puppeteer's own
  launcher can't start Edge here). Edge may sign the test profile into your
  Windows work or school account, so counts can be filed under that email rather
  than the placeholder; delete the test platform's database afterwards.
- It does not test force-install by policy or managed storage: those need a
  managed machine (see `../README.md`).

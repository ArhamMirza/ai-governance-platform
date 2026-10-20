# Deploying securely

These are the settings that matter when the platform is used by more than one
person on a network. None of it is needed on your own laptop.

## What to set

| Setting | Value | Why |
|---|---|---|
| `ENVIRONMENT` | `production` | Turns on the checks below, hides the API docs, and makes the first account need a setup code. |
| `SECRET_KEY` | a long random value | Encrypts stored AI provider keys and two-step sign-in secrets, and signs two-step sign-in tickets. The app refuses to start on the example value. Rotating it later makes those stored secrets unreadable (provider keys are re-entered; people with two-step sign-in use a recovery code, or an administrator resets them). Sessions are not affected. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `COOKIE_SECURE` | `true` | The session cookie is only sent over https, and takes the browser-enforced `__Host-` prefix. The app refuses to start without it. |
| `CORS_ORIGINS` | the exact address(es) people use, e.g. `https://governance.example.com` | A wildcard is refused. Not needed when the app and API share one address (see the proxy examples). |
| `SETUP_CODE` | optional | If you leave it unset the server makes one up at each start and prints it in its log. Needed once, to create the first account. |

## Run the API behind the proxy

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 \
  --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-server-header
```

- `--proxy-headers` with `--forwarded-allow-ips` makes the sign-in limits see each
  person's real address instead of the proxy's. List only the proxy's address.
- `--no-server-header` stops the server announcing what it is.
- Keep the API on `127.0.0.1` so it can only be reached through the proxy.

## The proxy

`Caddyfile.example` and `nginx.conf.example` serve the built app and forward `/api/`
to the API on one https address, with:

- a strict **Content-Security-Policy** (scripts only from the site itself),
- **Strict-Transport-Security**, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` and `Permissions-Policy`.

The API adds the same protections to its own responses, so they hold even if the proxy
is misconfigured. Build the frontend for a single address with
`VITE_API_BASE_URL=/api/v1 npm run build`.

The policy allows the Google Fonts stylesheet and font files, because the app's
typefaces are loaded from there. Self-hosting the fonts would let you remove both.

## First start

1. Start the API. Its log prints `enter this setup code: ...` (unless you set `SETUP_CODE`).
2. Open the site and create the first account with that code.
3. The code is not asked for again, and registration closes.
4. Turn on **two-step sign-in** for that account (*Your account*), save the recovery
   codes, then under *Users → Sign-in security* require it for administrators. The
   setting can only be switched on by an administrator who already has it.
5. Create the other accounts under *Users*. Each starts with a temporary password the
   person must replace at first sign-in.

## Check it

```bash
curl -sI https://governance.example.com/ | grep -i -E "content-security|strict-transport|x-frame|nosniff"
curl -sI https://governance.example.com/api/v1/health | grep -i -E "content-security|cache-control"
curl -s -o /dev/null -w "%{http_code}\n" https://governance.example.com/docs   # 404
```

## What is not covered here

- Rate limits for sign-in are kept in memory and reset when the API restarts. They also
  assume one API process; behind several, each counts separately.
- Backups, patching the host, and certificate renewal are yours to run.

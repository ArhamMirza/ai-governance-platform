# Security policy

## Reporting a vulnerability

Please report security problems **privately**, not in a public issue or pull request.

Use GitHub's private reporting: open the **Security** tab of this repository and choose
**Report a vulnerability**. Include what you found, how to reproduce it, and what you think
the impact is. A proof of concept against a local copy of the app is ideal; please don't test
against anyone else's deployment.

This is a personal project, so there is no service-level agreement, but reports are read and
taken seriously. Expect an acknowledgement within a few days. Credit is given in the fix
unless you would rather stay anonymous.

## Supported versions

Only the latest `main` is supported. There are no maintained release branches.

## What this project does for security

Sign-in and sessions: PBKDF2-HMAC-SHA256 password hashing (600,000 iterations), a 12-character
password rule with a check for common and personal passwords, lockouts, authenticator-app
two-step sign-in with recovery codes, hashed session tokens, `HttpOnly` / `SameSite=Strict`
(and `__Host-` prefixed over https) cookies, and an audit trail of sign-ins.

Web layer: security headers on every response, a cross-site request check, an explicit CORS
allow-list, no API docs in production, and a first-run setup code. Every route requires
a signed-in session by default, and a test walks every route as an employee login to check
that only the staff routes open.

Supply chain: `pip-audit` and `npm audit` run in CI, Dependabot is on, and the built frontend
is checked in CI for compatibility with a strict Content-Security-Policy.

The details are in the *Accounts and sign-in* and *Two-step sign-in* sections of the
[README](README.md) and in [deploy/README.md](deploy/README.md).

## Known limitations

This is a portfolio project. It has had no independent security review or penetration test,
and it is **not ready to hold a real organization's data** without more work:

- the database is a single SQLite file, with no automated backups and no encryption at rest;
- sign-in rate limits are kept in memory, so they reset on restart and assume one API process;
- uploaded evidence is parsed on the server by PDF, Word and OCR libraries, with no sandbox;
- authenticator codes can be phished (hardware keys are not supported);
- sessions last 14 days with no idle timeout;
- one organization per deployment.

The demo data (`python -m app.seed`) is entirely fictional. If you find real personal
data, credentials or keys committed anywhere in this repository's history, please report it
the same way.

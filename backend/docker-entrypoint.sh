#!/bin/sh
# Brings the database up to date, optionally loads demo data, then runs the API.
set -e

# Development mode relaxes the secret-key and cookie checks and lets anyone who
# reaches the page create the first account. That is fine for trying it out on this
# machine and wrong for anything reachable by other people, so refuse to start that
# way unless the app is only published on this machine.
if [ "${ENVIRONMENT:-development}" = "development" ]; then
    case "${WEB_BIND:-127.0.0.1}" in
        127.0.0.1|localhost|::1) ;;
        *)
            echo "Refusing to start: ENVIRONMENT=development while the app is published on" >&2
            echo "${WEB_BIND}. Anyone who can reach it could create the first (admin) account." >&2
            echo "Set ENVIRONMENT=production (with a real SECRET_KEY and COOKIE_SECURE=true," >&2
            echo "behind https), or set WEB_BIND=127.0.0.1. See deploy/README.md." >&2
            exit 1
            ;;
    esac
fi

alembic upgrade head

# Skips itself if the database already holds records, so it is safe on every start.
if [ "${DEMO_DATA:-false}" = "true" ]; then
    python -m app.seed
fi

# The only thing that can reach this port is the web container in front of it,
# so it is that container's address that is trusted to say where a request came from.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" --no-server-header

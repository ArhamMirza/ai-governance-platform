# Frontend

The React app for the [AI Governance Platform](../README.md): React 19, TypeScript, Vite,
TanStack Query v5, react-hook-form with zod, react-router, and plain CSS with design tokens
(light and dark). The architecture is described in [DESIGN.md](../DESIGN.md#9-frontend).

## Commands

Node 22 or newer (what CI runs, and what vitest requires).

```bash
npm install
cp .env.example .env     # VITE_API_BASE_URL, default http://localhost:8000/api/v1
npm run dev              # http://localhost:5173
npm test                 # vitest, about 800 tests
npm run lint             # oxlint
npm run build            # tsc -b && vite build
```

On a slow or busy machine, `npx vitest run --maxWorkers=2` avoids spurious timeouts.

To serve the built app and the API from one address, build with
`VITE_API_BASE_URL=/api/v1 npm run build` (see [../deploy/README.md](../deploy/README.md)).

## Layout

```
src/
├── app/           App.tsx (sign-in, forced-change gates and the employee/main split),
│                  routes.tsx, Layout.tsx, queryClient.ts
├── shared/        api/httpClient + readError, components/, dlp/detectors.ts, hooks, theme
├── features/<x>/  api.ts · hooks.ts · types.ts · components/ · __tests__/   (one per area)
└── pages/         route-level compositions of feature components
public/theme-init.js   sets the saved theme before first paint (a file, not inline script)
scripts/csp-check.mjs  fails if the built page could not run under a strict CSP
```

## Conventions

- **A feature owns its API.** `features/<x>/api.ts` is the only place that knows the URL
  shape; components never call `fetch`, so a test mocks one file.
- **Server state lives in React Query**; UI state in components. A 401 is data ("not signed
  in"), not an error.
- **No inline scripts.** The page must run under `script-src 'self'`. CI runs
  `node scripts/csp-check.mjs dist/index.html` after the build.
- **`shared/dlp/detectors.ts` is shared with the browser extension** (it imports it
  directly), so the rule tester here and the extension run identical code. A backend test
  checks that the built-in rule keys match.
- **Screens that show something once** (temporary passwords, recovery codes) hold it in
  local state and can't be dismissed by accident.
- Tests for screens that depend on how data refreshes use the real hooks with only the
  network faked (see `features/auth/__tests__/TwoStepFlow.test.tsx`); mocking the hooks
  would hide that class of bug.

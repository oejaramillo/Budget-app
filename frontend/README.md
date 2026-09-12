# Budget App — frontend

React 19 + Vite single-page client for the Budget App API.

Full documentation (setup, environment variables, API reference and deployment)
lives in the repository root: [`../README.md`](../README.md).

## Quick start

```bash
cp .env.example .env      # set VITE_API_URL to your backend
npm install
npm run dev               # http://localhost:5173
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server with HMR on port 5173 |
| `npm run build` | Production bundle in `dist/` |
| `npm run preview` | Serve the built bundle locally |
| `npm run lint` | ESLint over `src/` |

## Source layout

```
src/
  api.js                    axios instance, JWT refresh interceptor, error helper
  constants.js              API paths, endpoint table, enum options
  utils/format.js           money/date/percent formatting helpers
  services/                 one module per resource; the only place axios is called
  hooks/                    React Query wrappers (useAccounts, useBudgets, ...)
  components/
    ui/                     Field, Alert, StatCard, DataTable, FormPanel
    auth/                   landing page and sign-in/sign-up panel
    dashboard/              shell with tabs + overview tab
    accounts|transactions|categories|budgets|investments|currencies/
  styles/globals.css        design tokens and shared classes
```

### Conventions

* Plain JavaScript with JSDoc typedefs — no build-time type checking is configured.
* All HTTP goes through `services/*`; components never import `axios` directly.
* Money is treated as a string end-to-end. Never call `parseFloat` on an amount
  before sending it back to the API.
* Derived numbers (net worth, budget spend, transaction totals) come from the API,
  not from client-side arithmetic.

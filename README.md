# Budget App

A multi-tenant, multi-currency personal finance tracker. Log everyday income and
expenses, run budgets, keep an eye on investments and see everything converted
into the currency you actually think in.

* **Backend** — Django + Django REST Framework, PostgreSQL (Neon-ready)
* **Frontend** — React 19 + Vite, plain JavaScript with JSDoc types
* **Auth** — JWT (access + refresh), per-user data isolation everywhere
* **Money** — `Decimal` end to end; a float never touches an amount

---

## Table of contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Tech stack](#tech-stack)
4. [Repository layout](#repository-layout)
5. [Data model](#data-model)
6. [Quick start](#quick-start)
7. [Database setup: Neon (and local PostgreSQL)](#database-setup-neon-and-local-postgresql)
8. [Environment variables](#environment-variables)
9. [Common commands](#common-commands)
10. [API reference](#api-reference)
11. [Money and multi-currency rules](#money-and-multi-currency-rules)
12. [Security and multi-tenancy](#security-and-multi-tenancy)
13. [Testing](#testing)
14. [Deployment](#deployment)
15. [Project conventions](#project-conventions)
16. [Roadmap](#roadmap)
17. [Troubleshooting](#troubleshooting)

---

## Features

| Area | What works today |
| --- | --- |
| Accounts | Unlimited accounts per user: checking, savings, credit card, cash, investment, loan, other. Institution and account number fields, active/inactive flag. |
| Currencies | Shared ISO-4217 catalogue with a rate per currency, one "principal" reporting currency, and dated rate history for auditing. |
| Transactions | Income, expense and transfers. Categories, budgets, free-text description, and an explicit exchange rate when the transaction currency differs from the account. |
| Budgets | Period-based envelopes with a minimum and maximum, linked accounts, and live spend/remaining/percentage figures. |
| Investments | Holdings (stock, ETF, fund, bond, crypto, real estate, other) with quantity, cost basis and dated valuations, so gains are measured against a real value history. |
| Reporting | Period summary (income, expenses, net, per-category breakdown), monthly trend, net worth per currency, and portfolio totals — all convertible into a chosen currency. |
| Auth | Registration, JWT login, transparent access-token refresh, `/auth/me/` profile, staff-only administration. |
| Ops | Health endpoint, request throttling, pagination, audit trail of rate refreshes, Django admin. |

---

## Architecture

```
┌──────────────────────────────┐        ┌────────────────────────────────────────┐
│  React SPA (Vite)            │        │  Django + DRF                          │
│                              │        │                                        │
│  components/  ──▶  hooks/    │  HTTPS │  apps/users        auth + JWT          │
│      (React Query)           │ ─────▶ │  apps/currencies   catalogue + rates   │
│          │                   │  JSON  │  apps/accounts     money containers    │
│          ▼                   │        │  apps/budgets      envelopes           │
│      services/  ──▶ api.js   │        │  apps/transactions ledger + reports    │
│   (the only axios user)      │        │  apps/investments  holdings            │
└──────────────────────────────┘        └────────────────┬───────────────────────┘
                                                         │ psycopg2 (TLS)
                                                         ▼
                                          ┌────────────────────────────┐
                                          │ PostgreSQL — Neon          │
                                          └────────────────────────────┘
                                                         ▲
                                                         │ HTTPS
                                          ┌────────────────────────────┐
                                          │ exchangerate-api.com       │
                                          │ (rates, optional, 6h cron) │
                                          └────────────────────────────┘
```

The two halves are decoupled: the frontend knows only `VITE_API_URL` and the JSON
shapes described in the [API reference](#api-reference). That means the backend can
be redeployed, versioned (`/api/v1` → `/api/v2`) or replaced without touching React.

Request flow for a typical action:

```
form submit → useForm() → React Query mutation → services/*.js → api.js (JWT)
   → Django viewset → serializer validation → service-layer rules → PostgreSQL
   → invalidate derived queries → UI refreshes
```

---

## Tech stack

### Backend

| Package | Version | Why |
| --- | --- | --- |
| Django | 6.1 | Framework, admin, ORM |
| djangorestframework | 3.18 | API layer (viewsets, serializers, pagination, throttling) |
| djangorestframework-simplejwt | 5.5 | JWT access/refresh tokens |
| django-cors-headers | 4.9 | Lets the decoupled SPA call the API |
| django-filter | 26.1 | Querystring filtering on list endpoints |
| django-environ | 0.14 | Reads `.env` and parses `DATABASE_URL` |
| psycopg2-binary | 2.9 | PostgreSQL driver (Neon is plain PostgreSQL) |
| requests | 2.34 | Exchange-rate provider HTTP calls |
| gunicorn | 26 | WSGI server for deployment |
| whitenoise | 6.12 | Serves static files without a separate web server |

Deliberately **not** included: Celery/Redis (a management command on a scheduled
job is enough for rate refresh), `pytz` (Django 5+ uses `zoneinfo`), DRF's
token-auth app (JWT only), and any API-docs generator beyond Django's browsable API.

### Frontend

| Package | Version | Why |
| --- | --- | --- |
| react / react-dom | 19.1 | UI |
| @tanstack/react-query | 5.84 | Server-state caching, mutations, invalidation |
| axios | 1.10 | HTTP client with request/response interceptors |
| vite | 6.3 | Dev server and bundler |

`react-router-dom` and `jwt-decode` were removed: navigation is tab-based, and the
API is the authority on whether a token is still valid (no client-side `exp` math).

---

## Repository layout

```
Budget-app/
├── README.md                     ← you are here
├── .gitignore
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example              template — copy to .env (git-ignored)
│   ├── backend/                  Django project (settings package, urls, wsgi/asgi)
│   │   ├── settings/
│   │   │   ├── __init__.py       picks a profile via DJANGO_ENV
│   │   │   ├── base.py           everything shared; database + CORS + DRF config
│   │   │   ├── development.py    DEBUG, permissive CORS, console logging
│   │   │   └── production.py     fails fast on missing config, HTTPS/HSTS hardening
│   │   ├── urls.py               root URLconf, /api/v1/ namespace
│   │   └── pagination.py         shared page-size policy
│   └── apps/
│       ├── users/                register, login, refresh, me, health
│       ├── currencies/           Currency, rate snapshots/history, refresh command
│       ├── accounts/             Account + balances/net-worth endpoints
│       ├── budgets/              Budget + status endpoint
│       ├── transactions/         Category, Transaction, services.py, reports
│       └── investments/          Holding, Valuation, portfolio endpoints
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── .env.example
    └── src/
        ├── api.js                axios instance + JWT refresh interceptor
        ├── constants.js          API paths, endpoint table, enum options
        ├── utils/format.js       money/date/percent helpers
        ├── contexts/AuthContext.jsx
        ├── services/             one module per resource
        ├── hooks/                React Query wrappers + useForm
        ├── components/
        │   ├── ui/               Field, Alert, StatCard, DataTable, FormPanel
        │   ├── auth/             LandingPage, AuthPanel
        │   ├── dashboard/        DashboardShell (tabs), Dashboard (overview)
        │   └── accounts|transactions|categories|budgets|investments|currencies/
        └── styles/globals.css
```

Each Django app follows the same shape — `models.py`, `serializers.py`, `views.py`,
`urls.py`, `admin.py`, `tests.py` and (where needed) `services.py`. Anything that
touches money or balances lives in `services.py` so the API, the admin and the shell
all obey the same rules.

---

## Data model

```
User (django.contrib.auth)
 │
 ├── Account ────────────── currency ──▶ Currency ◀── principal (exactly one)
 │     │  name, account_type, balance,
 │     │  institution, official_number, is_active
 │     │
 │     ├── Transaction ──── category ──▶ Category ── budget ──▶ Budget
 │     │     │  transaction_type (income|expense|transfer),
 │     │     │  transaction_date, amount (always > 0),
 │     │     │  currency, exchange_rate (nullable),
 │     │     │  destination_account (transfers), budget
 │     │     └── source of every balance change
 │     │
 │     └── Holding ──────── currency ──▶ Currency
 │           │  symbol, kind, quantity, cost_basis
 │           └── Valuation (valued_on, value) — portfolio history
 │
 ├── Budget ── M2M ──▶ Account        (period, min/max, currency)
 └── Category ── FK ──▶ Budget         (optional, per-user name is unique)
```

Notable modelling decisions:

* `Transaction.amount` is **always positive**; direction comes from
  `transaction_type`. That removes a whole class of sign bugs, and
  `signed_amount` derives `-amount` for expenses and transfers.
* `Transaction.currency` defaults to the account currency and is validated in the
  service layer. A foreign currency requires an explicit `exchange_rate` so
  conversions remain auditable.
* `Account.balance` is a cached aggregate. It is read-only in the API and only
  changes through a transaction (or the explicit `adjust-balance` endpoint for an
  opening balance / reconciliation).
* Budgets link to accounts with an M2M field instead of a separate join model:
  one fewer table, and the ownership check stays trivial.
* `ExchangeRateSnapshot` + `ExchangeRateHistory` record every rate refresh so a bad
  provider response can be spotted (and reasoned about) later.

---

## Quick start

### Prerequisites

* Python 3.12+
* Node.js 20+ and npm
* A PostgreSQL database — a free [Neon](https://neon.tech) project is the
  recommended option (see the next section)

### 1. Backend

```bash
cd backend

python -m venv ../amb                 # or any virtualenv location
source ../amb/bin/activate

pip install -r requirements.txt

cp .env.example .env                  # then edit it (see Environment variables)
python -c "import secrets; print(secrets.token_urlsafe(64))"   # paste as DJANGO_SECRET_KEY

python manage.py migrate
python manage.py refresh_currencies --bootstrap   # creates the USD base currency
python manage.py createsuperuser                  # for /admin/ and rate editing
python manage.py runserver 8080                   # http://127.0.0.1:8080 due that port 80 is usually taken 
```

`.env` is optional for a first run: with nothing configured the project falls back
to SQLite and a development secret, so `migrate` and `runserver` always work. Set
`DATABASE_URL` (Neon) to move to PostgreSQL — see
[Database setup](#database-setup-neon-and-local-postgresql).

### 2. Frontend

```bash
cd frontend
cp .env.example .env      # VITE_API_URL=http://127.0.0.1:8000 by default
npm install
pm run dev -- --port 8081             # http://localhost:5173 due that port 80 is usually taken 
```

Open <http://localhost:5173>, create an account and start logging.

### 3. First five minutes

1. **Currencies → Add currency** (staff only) or run `manage.py refresh_currencies`
   to pull ~160 currencies from the provider. Mark your main one as *principal*.
2. **Accounts → Add account**, pick a currency, set an opening balance.
3. **Categories → Add category** (e.g. Groceries) and a **Budget** for the month.
4. **Transactions → Log transaction** — expenses and income update the account
   balance immediately; transfers move money between two of your accounts.
5. **Overview** shows net worth, this month's income/expenses/net, the monthly
   trend and a category breakdown. Use *Reporting currency* in the header to
   convert everything into another currency.

---

## Database setup: Neon (and local PostgreSQL)

[Neon](https://neon.tech) is serverless PostgreSQL with a generous free tier and
scale-to-zero, which matches this project's "lightweight and cost-efficient" goal.
Nothing Neon-specific is needed on the Django side: it is plain PostgreSQL over TLS.

### Create the database

1. Sign in at <https://console.neon.tech> and create a project
   (pick the region closest to where the backend will run).
2. Open **Dashboard → Connection string** and copy the **pooled** connection
   string. It looks like:

   ```
   postgresql://alex:AbC123dEf@ep-cool-darkness-123456-pooler.eu-central-1.aws.neon.tech/budget?sslmode=require
   ```

   * Use the **pooler** host endpoint (`-pooler`) for the Django app.
   * Use the **direct** host (without `-pooler`) for `migrate` if you ever see
     connection-pool limits during a long migration; Neon's docs recommend the
     direct endpoint for DDL-heavy work.
   * Never drop `?sslmode=require` — Neon rejects unencrypted connections.

### Point Django at it

**Option A — one variable (recommended).** In `backend/.env`:

```dotenv
DATABASE_URL=postgresql://alex:AbC123dEf@ep-cool-darkness-123456-pooler.eu-central-1.aws.neon.tech/budget?sslmode=require
DB_CONN_MAX_AGE=0
```

`DATABASE_URL` always wins over the discrete variables.

**Option B — discrete variables.** Useful when a host provides separate fields:

```dotenv
DB_NAME=budget
DB_USER=alex
DB_PASSWORD=AbC123dEf
DB_HOST=ep-cool-darkness-123456-pooler.eu-central-1.aws.neon.tech
DB_PORT=5432
DB_SSLMODE=require
```

Both `DB_HOST` and `DB_NAME` must be set for this branch to activate.

### Apply the schema

```bash
cd backend
python manage.py migrate
python manage.py refresh_currencies      # needs EXCHANGE_API_KEY
python manage.py createsuperuser
```

### Verify

```bash
python manage.py dbshell -c "select version();"
curl http://127.0.0.1:8000/api/v1/health/
# {"status":"ok","database":true}
```

### Connection pooling notes

* `DB_CONN_MAX_AGE` keeps a connection open between requests. With the Neon
  **pooler** endpoint and a long-running container (gunicorn/Render/Railway),
  `0`–`60` is fine because the pooler multiplexes for you. Use `0` on serverless
  platforms that freeze the process between requests.
* Neon closes idle connections; Django's default behaviour of reconnecting per
  request with `CONN_MAX_AGE=0` is the safest default and is what the templates use.
* **Local PostgreSQL** needs no special handling — set the same variables with
  `DB_HOST=localhost` and drop `DB_SSLMODE` (or set it to `disable`).

---

## Environment variables

All backend variables live in `backend/.env` (git-ignored). `backend/.env.example`
is the documented template.

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | *(empty)* | **Required in production.** Generate with `secrets.token_urlsafe(64)`. Placeholders are rejected. |
| `DJANGO_ENV` | `development` | `development` or `production`. Selects the settings profile. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma separated. Production rejects `*` and empty values. |
| `DATABASE_URL` | *(empty)* | Neon/PostgreSQL connection string. Takes precedence. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | *(empty)* / `5432` | Alternative to `DATABASE_URL`; needs both `DB_HOST` and `DB_NAME`. |
| `DB_SSLMODE` | `require` | Set `disable` for a local PostgreSQL. |
| `DB_CONN_MAX_AGE` | `0` | Seconds to reuse a connection. |
| `CORS_ALLOWED_ORIGINS` | *(empty)* | Frontend origins, with scheme. Required in production. |
| `CSRF_TRUSTED_ORIGINS` | *(empty)* | Same origins, needed for the Django admin over HTTPS. |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | `30` | Short by design; the SPA refreshes silently. |
| `REFRESH_TOKEN_LIFETIME_DAYS` | `7` | |
| `EXCHANGE_API_KEY` | *(empty)* | Free key from exchangerate-api.com. Optional. |
| `EXCHANGE_API_BASE_URL` | `https://v6.exchangerate-api.com/v6` | |

> **Precedence:** real environment variables win over `backend/.env`, and the file is
> read whenever it exists. On a host that injects its own variables (Render, Fly,
> Railway) you can deploy without a `.env` file — but remember that a stale local
> `.env` will supply development values and mask the difference when you test a
> production configuration on your machine.

Production refuses to start when any of these is true: `DJANGO_SECRET_KEY` is
missing or is a placeholder/development value, `DJANGO_ALLOWED_HOSTS` is empty or
`*`, `CORS_ALLOWED_ORIGINS` is empty, or no PostgreSQL database is configured.

Frontend variables live in `frontend/.env`:

| Variable | Default | Notes |
| --- | --- | --- |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend origin, no trailing slash. |

> Only `VITE_`-prefixed values reach the browser bundle. Never put secrets there.

---

## Common commands

Run from `backend/` with the virtualenv active.

```bash
python manage.py runserver                  # dev server on :8000
python manage.py migrate                    # apply migrations
python manage.py makemigrations <app>       # create migrations after model changes
python manage.py createsuperuser
python manage.py test                       # full test suite
python manage.py test apps.transactions     # one app
python manage.py check                      # system checks
python manage.py check --deploy             # production-hardening checklist
python manage.py refresh_currencies         # fetch rates (skips if < 6h old)
python manage.py refresh_currencies --force # ignore the staleness guard
python manage.py refresh_currencies --no-create   # refresh known currencies only
python manage.py refresh_currencies --bootstrap   # base currency only, no network
python manage.py shell
```

From `frontend/`:

```bash
npm run dev        # dev server on :5173
npm run build      # production bundle in dist/
npm run preview    # serve dist/ locally
npm run lint       # ESLint
```

> **Note on migrations:** `manage.py test` and `makemigrations` must be run from
> `backend/`. The `.gitignore` deliberately does **not** ignore `migrations/` —
> migrations are application code and belong in version control.

---

## API reference

Base URL: `http://127.0.0.1:8000/api/v1/`

Authentication: `Authorization: Bearer <access_token>` on every endpoint except
registration, login, refresh and health.

List endpoints are paginated: `{count, next, previous, results}` with
`?page=`, `?page_size=` (max 500), `?search=`, `?ordering=` and per-resource
filters.

### Authentication — `apps/users`

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register/` | — | Create an account. Body: `username`, `password`, `password_confirm`, optional `email`. Throttled 10/min. |
| POST | `/auth/login/` | — | JWT login → `{access, refresh}`. Throttled 10/min. |
| POST | `/auth/refresh/` | — | Exchange a refresh token for a new access token (rotation enabled). |
| POST | `/auth/verify/` | — | Check a token is still valid. |
| GET | `/auth/me/` | ✔ | Current user profile. |
| PATCH | `/auth/me/` | ✔ | Update `email`, `first_name`, `last_name`. |
| GET | `/health/` | — | `{"status": "ok", "database": true}`; 503 when the DB is unreachable. |

### Currencies — `apps/currencies`

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/currencies/` | user | List the catalogue. Filters: `code`, `is_active`, `principal`. |
| GET | `/currencies/{id}/` | user | One currency. |
| POST/PUT/PATCH/DELETE | `/currencies/{id}/` | **staff** | Manage the catalogue. |
| GET | `/currencies/{id}/convert/?target=EUR&amount=100` | user | Convert with the stored cross rate. |
| GET | `/currencies/summary/?target=EUR` | user | Total balance per currency, converted when `target` is given. |
| POST | `/currencies/refresh/` | **staff** | Re-fetch all rates from the provider (body: optional `{"base": "EUR"}`). |

### Accounts — `apps/accounts`

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/accounts/` | List / create. Filters: `account_type`, `currency`, `institution`, `is_active`. |
| GET/PUT/PATCH/DELETE | `/accounts/{id}/` | Retrieve / update / delete. `balance` is read-only. |
| POST | `/accounts/{id}/adjust-balance/` | Set a balance explicitly (`{"balance": "1500.00"}`). |
| GET | `/accounts/balances/?target=EUR` | Every account with an optional converted reference value. |
| GET | `/accounts/net-worth/?target=EUR` | Totals per currency plus the converted total. |

### Budgets — `apps/budgets`

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/budgets/` | List / create. `accounts` accepts a list of account IDs you own. |
| GET/PUT/PATCH/DELETE | `/budgets/{id}/` | Retrieve / update / delete. |
| GET | `/budgets/status/` | Limit, spent, remaining, `percentage_used`, `is_over_budget`. |

### Categories and transactions — `apps/transactions`

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/categories/` | List / create. Filters: `budget`, `is_active`. |
| GET/PUT/PATCH/DELETE | `/categories/{id}/` | Retrieve / update / delete. |
| GET/POST | `/transactions/` | List / create. Filters: `account`, `destination_account`, `category`, `budget`, `transaction_type`, `transaction_date`. |
| GET/PUT/PATCH/DELETE | `/transactions/{id}/` | Retrieve / update / delete. Balances are re-adjusted on every write. |
| POST | `/transactions/bulk/` | Atomic array of up to 100 transactions — either all land or none. |
| GET | `/transactions/summary/?start=&end=&target=` | Income, expenses, net, per-category breakdown. Defaults to the current month. |
| GET | `/transactions/monthly/?months=6` | Totals grouped by month (1–36). |

### Investments — `apps/investments`

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/holdings/` | List / create. Filters: `kind`, `currency`, `account`. |
| GET/PUT/PATCH/DELETE | `/holdings/{id}/` | Retrieve / update / delete. |
| GET | `/holdings/portfolio/?target=EUR` | Totals, gain, percentage and a per-kind breakdown. |
| GET | `/holdings/history/` | Portfolio value per valuation date. |
| GET/POST | `/valuations/` | List / create valuations. |
| GET/PUT/PATCH/DELETE | `/valuations/{id}/` | Retrieve / update / delete. |

### Example session

```bash
API=http://127.0.0.1:8000/api/v1

# Register, then log in
curl -X POST $API/auth/register/ -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo-password-123","password_confirm":"demo-password-123"}'

TOKEN=$(curl -s -X POST $API/auth/login/ -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo-password-123"}' | python -c 'import json,sys;print(json.load(sys.stdin)["access"])')

# Create an account and give it an opening balance
ACCOUNT=$(curl -s -X POST $API/accounts/ -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Main checking","account_type":"checking","currency":1}' | python -c 'import json,sys;print(json.load(sys.stdin)["id"])')

curl -X POST $API/accounts/$ACCOUNT/adjust-balance/ -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"balance":"1500.00"}'

# Log an expense — the balance drops automatically
curl -X POST $API/transactions/ -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"account":1,"transaction_type":"expense","transaction_date":"2026-01-15","amount":"25.50","description":"Groceries"}'

# This month's summary
curl "$API/transactions/summary/" -H "Authorization: Bearer $TOKEN"
```

A browsable version of every endpoint is available at
<http://127.0.0.1:8000/api/v1/> once you are logged into the Django admin in the
same browser session.

---

## Money and multi-currency rules

1. **No floats, ever.** Amounts are `Decimal` in Python and decimal *strings* in
   JSON. Precision is explicit per field: money is `DecimalField(max_digits=20,
   decimal_places=2)`, holding quantities use 10 decimal places (`max_digits=28`),
   and exchange rates use 12 (`max_digits=24`).
2. **Direction comes from the type, not the sign.** `amount` is always `> 0`
   (enforced by a database `CHECK` constraint). `signed_amount` is what the ledger
   applies.
3. **One rate convention.** `Currency.exchange_rate` is *units of this currency per
   1 unit of the base currency* (`BASE_CURRENCY_CODE`, USD by default), so the base
   currency's rate is exactly `1`. A cross rate is a single division:
   `amount * (target.rate / source.rate)`.
4. **Explicit conversion only.** Nothing is converted behind your back: endpoints
   return raw per-currency totals unless you pass `?target=CODE`.
5. **Explicit rates on cross-currency transactions.** If a transaction's currency
   differs from its account's, the request must include `exchange_rate` — otherwise
   the API returns 400. The account balance is affected in the account's currency.
6. **Balances are derived.** The API treats `balance` as read-only. It changes via
   transactions (and is corrected when a transaction is edited or deleted) or via
   `adjust-balance` for an opening balance.
7. **One principal currency.** A partial unique index guarantees at most one
   currency has `principal=True`.

---

## Security and multi-tenancy

* **Per-user scoping by construction.** Every viewset builds its queryset with
  `.filter(user=self.request.user)` — including list, retrieve, update and delete.
  Another tenant's object is a `404`, never a `403`, so IDs cannot be probed.
* **Ownership is re-checked on related objects.** `apps/transactions/services.py`
  resolves `account`, `destination_account`, `category` and `budget` and rejects
  anything not owned by the requester, with an identical message for "missing" and
  "someone else's" so nothing leaks. Serializer field querysets are scoped to the
  user as well, so a crafted request fails validation rather than at the database.
* **`user` cannot be spoofed.** It is read-only in every serializer and always set
  from the request.
* **Passwords** go through Django's validators (length, common-password, numeric,
  similarity) and are written with `create_user`. Registration and login are
  throttled to 10 requests/minute per IP, anonymous traffic to 30/minute, and each
  authenticated user gets 1000 requests/hour.
* **JWT** access tokens live 30 minutes; refresh tokens rotate. The SPA keeps them
  in `localStorage` and refreshes transparently on the first `401`.
* **Shared reference data is staff-only to modify.** Any user may read currencies
  and rates; only staff may change them, because a single edited rate would skew
  every tenant's reports.
* **Production hardening** (`settings/production.py`) refuses to boot without a
  secret key, real `ALLOWED_HOSTS` and explicit CORS origins; it also enables
  HTTPS redirect, HSTS, secure cookies, `X-Frame-Options: DENY` and
  `X-Content-Type-Options: nosniff`.
* **Secrets stay out of git.** `.env` is ignored; only `*.env.example` templates are
  committed.

### Planned hardening

* Move JWTs out of `localStorage` into `HttpOnly` cookies (needs CSRF plumbing).
* Per-user currency preferences instead of one app-wide principal currency.
* `django-axes`-style lockout after repeated failed logins.
* A `username`/`email` change flow that requires re-authentication.

---

## Testing

```bash
cd backend
python manage.py test                 # 95 tests, ~45s
python manage.py test apps.transactions
python manage.py test apps.accounts.tests.AccountIsolationTests
```

The suite focuses on the things that would be expensive to get wrong:

| File | Covers |
| --- | --- |
| `apps/users/tests.py` | Registration validation, weak/duplicate passwords, login, `/me/`, health. |
| `apps/currencies/tests.py` | Decimal conversion, float rejection, single-principal constraint, staff-only writes, `/convert/`. |
| `apps/accounts/tests.py` | **Cross-user isolation** (list/retrieve/update/delete), read-only balances, `adjust-balance`, net worth and conversion, pagination. |
| `apps/transactions/tests.py` | **Cross-user isolation**, balance effects for income/expense/transfer, revert on delete, `0.10 + 0.20` exactness, transfer/category/budget rules, foreign-currency rate requirement, atomic bulk insert, summary and monthly reporting. |
| `apps/budgets/tests.py` | Date/amount validation, ownership, account-link scoping, status and overspend detection. |
| `apps/investments/tests.py` | Symbol/quantity handling, valuation history, portfolio totals and conversion, per-kind grouping. |

Frontend checks are `npm run lint` and `npm run build` (Vite fails on unresolved
imports). There is no component test runner yet — see the [roadmap](#roadmap).

---

## Deployment

The frontend and backend are separate deployables. Two shapes are supported; pick
one based on how much you want to spend versus how simple you want the setup.

### Option A — fully decoupled (frontend on Vercel/Netlify, backend on Render/Fly/Railway)

Recommended when you want a CDN-served SPA and an independent API.

**Backend** (example: Render Web Service, Docker-free):

```bash
# Build command
pip install -r requirements.txt && python manage.py collectstatic --noinput
# Start command
python manage.py migrate --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
```

Environment (`DJANGO_ENV=production` plus):

```dotenv
DJANGO_ENV=production
DJANGO_SECRET_KEY=<64-byte random string>
DJANGO_ALLOWED_HOSTS=budget-api.onrender.com
DATABASE_URL=postgresql://...@ep-xxx-pooler.eu-central-1.aws.neon.tech/budget?sslmode=require
CORS_ALLOWED_ORIGINS=https://budget.vercel.app
CSRF_TRUSTED_ORIGINS=https://budget.vercel.app
EXCHANGE_API_KEY=<your key>
```

**Frontend** (Vercel/Netlify):

```dotenv
VITE_API_URL=https://budget-api.onrender.com
```

Build command `npm run build`, publish directory `dist`.

**Scheduled rate refresh** — a cron job on the backend host (or a GitHub Action
hitting an internal endpoint) running `python manage.py refresh_currencies`.
Daily is plenty; the command skips work when rates are less than six hours old.

### Option B — single service (Django serves the built SPA)

Cheapest: one process, one database, no CORS at all.

```bash
cd frontend && npm ci && npm run build        # produces frontend/dist
cd ../backend
pip install -r requirements.txt
export DJANGO_ENV=production
python manage.py collectstatic --noinput      # WhiteNoise picks up staticfiles/
python manage.py migrate --noinput
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
```

Then serve the SPA from Django: add `frontend/dist` to `TEMPLATES[0]["DIRS"]` and a
catch-all route returning `index.html` for non-`/api/`, non-`/admin/`, non-static
paths. Set `VITE_API_URL` to the same origin (or leave it empty and let requests be
relative). WhiteNoise is already wired into `settings/production.py`, so hashed
static assets are served with long-lived cache headers.

| | Option A | Option B |
| --- | --- | --- |
| Cost | Free tiers for both halves | One free/cheap service |
| Cold starts | API cold start only | Whole app cold starts together |
| CORS/CSRF | Must be configured | Not applicable |
| Frontend caching | CDN edge | App server (WhiteNoise) |
| Deploy independence | Full | Coupled |

Either way, run `python manage.py check --deploy` before going live.

---

## Project conventions

**Backend**

* One app per domain, each self-contained. Cross-app imports go through models,
  serializers or `services.py` — never through views.
* Business rules that touch money live in `services.py`, not in serializers, so the
  admin and management commands share them.
* Serializers are the only place input is validated; `validate_<field>` for one
  field, `validate()` for cross-field rules. Model `Meta.constraints` are the last
  line of defence.
* Related-field querysets in serializers are scoped to `request.user` in
  `__init__`.
* Every model change ships with a migration, committed to git.
* Docstrings explain *why* a rule exists, not what the line does.

**Frontend**

* Plain JavaScript with JSDoc typedefs. There is no `tsconfig.json` on purpose:
  adding type checking would mean a TypeScript build step and more dependencies.
* Components never import `axios`; all HTTP lives in `services/*`.
* Server state is React Query's job, form state is `useForm`'s, and there is no
  global store.
* One file per resource area (`AccountsManager`, `TransactionsManager`, …), with
  forms and tables inline while they stay small.
* Money is handled as a string. No arithmetic on amounts in the browser.
* `npm run lint` must pass; `npm run build` must succeed.

---

## Roadmap

Known gaps, roughly in priority order.

1. **Per-user principal currency.** Today `principal` is app-wide, which is fine
   for a single-operator instance but wrong for a true multi-tenant service. Move
   the preference onto a `UserProfile` model and keep the catalogue shared.
2. **Investments UI depth.** The API supports valuations; the UI does not yet chart
   portfolio history or let you edit a valuation inline.
3. **Transaction import.** CSV/bank-statement import (the atomic `/transactions/bulk/`
   endpoint was built with this in mind).
4. **Recurring transactions** and scheduled income/expenses.
5. **Frontend tests.** Vitest + React Testing Library on the money formatting, the
   auth refresh interceptor and the form error mapping.
6. **API schema and docs.** `drf-spectacular` for an OpenAPI file, then generated
   client types.
7. **HTTP-only cookie auth** instead of `localStorage` (see
   [Planned hardening](#planned-hardening)).
8. **Soft delete / restore** for accounts and transactions, plus an audit log.
9. **CSV/PDF export** for tax season.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'requests'`**
`pip install -r requirements.txt` inside the active virtualenv.

**`django.db.utils.OperationalError: connection ... failed` on Neon**
Checklist: the connection string ends with `?sslmode=require`; you used the
`-pooler` host; the password has no unescaped special characters (percent-encode
them); Neon's compute is not suspended (the first request after idle can take a
second).

**`ERROR: That port is already in use`**
Another dev server is still running. Find it with
`ss -ltnp | grep 8000` (or `5173`) and stop it, or run
`python manage.py runserver 8010`.

**Frontend loads but every request fails in the console**
`VITE_API_URL` is wrong or the backend is not running. Remember to restart the Vite
dev server after editing `frontend/.env` — Vite only reads it at startup.

**`CORS` errors in the browser**
In development `CORS_ALLOW_ALL_ORIGINS=True` is forced, so a CORS failure usually
means the request never reached Django. In production, add the exact frontend
origin (scheme included, no trailing slash) to `CORS_ALLOWED_ORIGINS` and the same
value to `CSRF_TRUSTED_ORIGINS`.

**`403 Forbidden` when adding a currency**
The currency catalogue is staff-only. Grant staff with
`python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.get(username='you'); u.is_staff=True; u.save()"`.

**`400` on a transaction with `currency:` set**
If the currency differs from the account's, `exchange_rate` is required. Either drop
`currency` (the account currency is used) or send an explicit rate.

**Transactions exist but the account balance looks wrong**
Use `POST /api/v1/accounts/{id}/adjust-balance/` to reconcile, and check the
`/transactions/` list for a bookmarked gap. Balances are recomputed from the moment
this app started tracking them; manually entered opening balances belong in
`adjust-balance`.

**Tests hang or fail to discover**
Run `python manage.py test` from `backend/`, not from the repository root.

---

## License

No license file is present yet. Until one is added, treat the code as
all-rights-reserved by the author.

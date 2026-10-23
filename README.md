# KohaRoute

Pickup booking and route planning for Auckland Community Centre. Team Koha.

This is **Parts 0 and 1**: the foundation, then the data models, business settings and seed
script. Features arrive one part at a time (Part 2 adds login).

## Folder layout

```
koharoute/
  environment.yml        conda environment (KOHA-ROUTE, Python 3.11)
  backend/
    app/                 FastAPI code
      models/            database tables (one file per table)
      services/          business rules: settings reader, open-day calendar
      api/               HTTP routers
      seed.py            `python -m app.seed` (logic) and seed_data.py (the data itself)
      security.py        password hashing
      config.py, database.py, timeutil.py
    tests/               pytest tests
    requirements*.txt    packages
    pyproject.toml       Black, Ruff and pytest settings
    .env.example         copy to .env to override defaults
  frontend/
    src/api/             one small file per backend resource, plus a shared fetch wrapper
    src/hooks/           reusable React logic (no screen markup)
    src/pages/           one file per screen
    src/theme.js         colours and type for the whole app
  scripts/               comparison script for the Project Report (added in Part 10)
```

## One-time setup

You need conda and Node.js 20 or newer.

```bash
# Backend
conda env create -f environment.yml
conda activate KOHA-ROUTE
cd backend
python -m pip install -r requirements-dev.txt

# Frontend (in a second terminal)
cd frontend
npm install
```

## Run it

```bash
# Terminal 1, from backend/ (environment KOHA-ROUTE active)
uvicorn app.main:app --reload        # http://localhost:8000/api/health and /docs

# Terminal 2, from frontend/
npm run dev                          # http://localhost:5173
```

The start page shows a "Setup check" with Backend, Database, today's NZ date and the version.

## Create the database and seed it

From `backend/`, with the `KOHA-ROUTE` environment active:

```bash
python -m app.seed             # create tables, add anything missing (safe to repeat)
python -m app.seed --reset     # wipe everything first, then seed (asks you to type "yes")
```

Running it twice is safe: the second run reports "already seeded" and changes nothing.

| Seeded item | On re-run |
| --- | --- |
| Settings (opening days, window, size presets, depot, ...) | Rewritten from `app/seed_data.py`. This is how a rule is changed in the MVP. |
| Closed dates, categories, vehicles, demo bookings | Added only if missing; never overwritten |
| Users (1 Admin, 3 drivers) | Added only if missing; an existing account keeps its password |

Demo logins: `admin@koharoute.test` and `driver1@koharoute.test` to `driver3@koharoute.test`.
Their passwords come from `SEED_ADMIN_PASSWORD` and `SEED_DRIVER_PASSWORD` (see
`backend/.env.example`; demo use only, at least 10 characters).

The demo data is 10 fictional bookings: six Approved on the next open day (160 kg and 730 L in
total, a realistic day to plan), three Pending and one Rejected. They have no photos.

## Test and format

```bash
# backend/
python -m pytest
python -m ruff check .
python -m black --check .            # drop --check to fix formatting

# frontend/
npm test
npm run format:check                 # use `npm run format` to fix
```

## Configuration

Settings come from environment variables or `backend/.env` (see `.env.example`):
`KOHA_ENV`, `DATABASE_URL` (default `backend/koharoute.db`) and `CORS_ORIGINS`.
Business rules such as opening days and size presets are stored in the database from Part 1,
not in configuration.

## Where each coding standard is demonstrated

| Standard | Examples in Part 0 |
| --- | --- |
| Modularity and encapsulation | `config.py` (settings only), `database.py` (all SQLite details), `timeutil.py` (the only place "today" is decided), `api/health.py` (one router per feature); `settings_service` is the only code that reads setting rows; `calendar_service` is pure functions with no database; frontend split into `api/`, `hooks/`, `pages/` |
| Performance | One cached config read (`lru_cache`); one session per request, always closed; SQLite write-ahead logging; shared in-memory connection in tests; `AbortController` cancels stale requests; indexes on booking status, pickup date, reference and photo booking; `lazy="selectin"` avoids one query per booking; all settings read in one query; seed runs in one transaction |
| Commenting and documentation | Google-style docstrings on every public function (enforced by Ruff rule set `D`); comments explain why (for example, why `date.today()` is banned); JSDoc on the frontend helpers; the seed data cites its source and date; this README |
| Indentation and formatting | Black and Ruff (4 spaces, 100 columns) via `pyproject.toml`; Prettier (2 spaces, single quotes) via `.prettierrc.json`; `.editorconfig` for every editor |
| Naming conventions | `snake_case` functions and files, `PascalCase` classes and React components, `UPPER_SNAKE_CASE` constants, `camelCase` JavaScript; names follow the spec vocabulary |

## Data model (Part 1)

| Table | Holds |
| --- | --- |
| `settings` | Business rules as key/value rows (JSON values) |
| `closed_dates` | NZ public holidays that fall on weekdays, 2026 and 2027 |
| `categories` | Item categories on the booking form |
| `users` | Admin and drivers (role is checked by the database) |
| `vehicles` | Capacity in whole kg and whole litres |
| `bookings` | Donor requests, with estimated kg and litres and one of the six statuses |
| `booking_categories` | Which categories a booking has |
| `photos` | Photo metadata (random stored name; the file lives on disk) |

Routes and stops arrive in Part 7.

## Holiday data

Closed dates come from the Employment New Zealand page on public holidays and anniversary
dates (checked 15 Oct 2026). A holiday that falls on a weekend is listed on the Monday or
Tuesday it is observed. That page warns that regional anniversary dates may contain errors, so
confirm Auckland Anniversary Day (26 Jan 2026 and 1 Feb 2027) with the client before release.

## Known limits

- Login, bookings and routes are not built yet.
- The size presets, vehicle capacities, categories and depot coordinates are placeholders
  awaiting client confirmation. The depot coordinates are approximate until Part 3 looks them up.
- There is no migration tool: the schema is created from the models. After a model change in
  development, run `python -m app.seed --reset`.

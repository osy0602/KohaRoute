# KohaRoute

Pickup booking and route planning for Auckland Community Centre. Team Koha.

This repository currently includes Parts 0-6: the foundation, seeded data/settings, staff login,
donor pickup booking and tracking, Admin booking review, and vehicle management. Later features
arrive one part at a time.

## Folder layout

```
koharoute/
  environment.yml        conda environment (KOHA-ROUTE, Python 3.11)
  backend/
    app/                 FastAPI code
      models/            database tables (one file per table)
      services/          business rules, booking, photo and ORS adapters
      api/               HTTP routers
      seed.py            `python -m app.seed` (logic) and seed_data.py (the data itself)
      security.py        password hashing
      config.py, database.py, timeutil.py
    tests/               pytest tests
    requirements*.txt    packages
    pyproject.toml       Black, Ruff and pytest settings
    .env.example         copy to .env for ORS key and local overrides
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

The public start page is the donor pickup booking form. Staff use `/login`.

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
`KOHA_ENV`, `DATABASE_URL` (default `backend/koharoute.db`), `CORS_ORIGINS`, `ORS_API_KEY`,
and `PHOTO_STORAGE_DIR`. Set a unique `JWT_SECRET_KEY` outside local development. Uploaded
photos default to `backend/uploads/photos/` and are not served as public static files.
Business rules such as opening days and size presets are stored in the database from Part 1,
not in configuration.

## Donor booking (Part 3)

The public form loads open pickup dates, active categories, size presets, and upload limits from
`GET /api/bookings/options`. Address autocomplete uses `GET /api/bookings/address-suggestions`
and requires an `ORS_API_KEY`; selections are signed and expire after ten minutes. Submit a
multipart form to `POST /api/bookings`. The backend revalidates all fields, calculates estimates,
decodes and re-encodes JPG/PNG photos to remove metadata, and stores photos under random names.
The confirmation contains a random reference; tracking arrives in Part 4. If address search is
unavailable, configure a valid ORS key and retry.

## Track a booking (Part 4)

Donors can use `/track` or `GET /api/bookings/track/{reference}` to see the booking status and
pickup date. The response includes only the pickup area, not the street address, donor name,
contact number, or photo details. Rejected bookings include the Admin's reason; missed bookings
show that the centre will contact the donor to reschedule. Unknown references return
`No booking found`.

## Admin booking review (Part 5)

Admins review bookings at `/admin`. The list defaults to Pending and supports status and pickup-date
filters. Admins can open details, including contact, description, photos, estimated load, and a map
preview. Pending bookings can be approved or rejected with a reason; Approved or Missed bookings
can be rescheduled to an open date. Review, transition, and photo endpoints are protected by the
server-side Admin role guard. Photos are served from private storage only through the authenticated
Admin photo endpoint.

## Vehicle management (Part 6)

Admins manage vehicles at `/admin/vehicles`. The list shows name, plate, capacity in kg and m³,
and Active/Inactive status. Vehicles can be added or edited, but not deleted; deactivation is a
soft status change. Plate numbers are normalized to uppercase and limited to six alphanumeric
characters, and capacities must be positive whole numbers. Vehicle endpoints require the Admin
role. Route assignments are introduced in Part 7; the shared deactivation guard rejects Planned
or In progress route statuses once persisted assignments are connected.

## Where each coding standard is demonstrated

| Standard | Examples across the current parts |
| --- | --- |
| Modularity and encapsulation | `config.py` (settings only), `database.py` (all SQLite details), `timeutil.py` (the only place "today" is decided), `api/health.py` (one router per feature); `settings_service` is the only code that reads setting rows; `calendar_service` is pure functions with no database; frontend split into `api/`, `hooks/`, `pages/` |
| Performance | One cached config read (`lru_cache`); one session per request, always closed; SQLite write-ahead logging; shared in-memory connection in tests; `AbortController` cancels stale requests; indexes on booking status, pickup date, reference and photo booking; `lazy="selectin"` avoids one query per booking; all settings read in one query; seed runs in one transaction |
| Commenting and documentation | Google-style docstrings on every public function (enforced by Ruff rule set `D`); comments explain why (for example, why `date.today()` is banned); JSDoc on the frontend helpers; the seed data cites its source and date; this README |
| Indentation and formatting | Black and Ruff (4 spaces, 100 columns) via `pyproject.toml`; Prettier (2 spaces, single quotes) via `.prettierrc.json`; `.editorconfig` for every editor |
| Naming conventions | `snake_case` functions and files, `PascalCase` classes and React components, `UPPER_SNAKE_CASE` constants, `camelCase` JavaScript; names follow the spec vocabulary |

Part 3 keeps booking rules, address search, photo processing, persistence, API schemas, and UI in
separate modules. ORS uses one shared async HTTP client, bounded five-minute query caching, and
per-client rate limiting. Booking validation and image preparation happen before persistence;
failed database writes roll back and remove any already-written photo files.

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

- Route generation, driver workflow, and the operational map/totals are not built yet.
- The size presets, vehicle capacities, categories and depot coordinates are placeholders
  awaiting client confirmation. The depot coordinates are approximate pending a later ORS lookup.
- There is no migration tool: the schema is created from the models. After a model change in
  development, run `python -m app.seed --reset`.

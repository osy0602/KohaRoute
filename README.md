# KohaRoute

Pickup booking and route planning for **Te Manawa Community Centre**. Built by Team Koha.

Donors book a pickup of items online and track its progress with no account. Admin staff review
bookings, manage vehicles and generate optimised pickup routes. Drivers follow their assigned route
on a map and mark each stop Completed or Missed.

## Contents

1. [Features](#1-features)
2. [Technology](#2-technology)
3. [Installation and configuration (step by step)](#3-installation-and-configuration-step-by-step)
4. [Operating the system](#4-operating-the-system)
5. [Testing and formatting](#5-testing-and-formatting)
6. [Project files and their purpose](#6-project-files-and-their-purpose)
7. [API summary](#7-api-summary)
8. [Data model](#8-data-model)
9. [Coding standards](#9-coding-standards)
10. [Licence](#10-licence)
11. [Credits](#12-credits)

---

## 1. Features

| Role | What they can do | Page |
| --- | --- | --- |
| Donor (no login) | Book a pickup: choose an open date, categories, size, address (autocomplete), up to the allowed number of JPG/PNG photos | `/book` |
| Donor (no login) | Track a booking by its reference: status, pickup date, area only (no street address) | `/track` |
| Admin | Review bookings; approve, reject (with reason) or reschedule; view photos and a map preview | `/admin` |
| Admin | Add and edit vehicles; activate/deactivate (never delete) | `/admin/vehicles` |
| Admin | Pick a date, drivers and vehicles; generate optimised routes; view the map and daily totals | `/admin/routes` |
| Driver | See only their own route for a day; next stop first; navigate with Google Maps; mark Completed or Missed (Missed needs a remark) | `/driver` |


## 2. Technology

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2, SQLite (WAL mode), Pydantic 2, httpx, bcrypt, Pillow.
- **Frontend:** React 18, Vite 5, Material UI 6, React Router 6, Leaflet / React-Leaflet, `@mapbox/polyline`, Vitest.
- **External service:** [OpenRouteService](https://openrouteservice.org) (ORS) for address search and route optimisation.
- **Tooling:** conda, pytest, Ruff, Black, Prettier.

## 3. Installation and configuration (step by step)

### 3.1 Prerequisites

- [conda](https://docs.conda.io/) (Miniconda or Anaconda)
- Node.js 20 or newer (includes npm)
- Git
- A free ORS API key from <https://openrouteservice.org/dev/#/signup> (required for address search and route generation)

### 3.2 Get the code

```bash
git clone <repository-url> KohaRoute
cd KohaRoute
```

If you received a zip file instead, unzip it and `cd` into the `KohaRoute_B` folder.

### 3.3 Backend setup

```bash
conda env create -f environment.yml      # creates the KOHA-ROUTE environment (Python 3.11)
conda activate KOHA-ROUTE
cd backend
python -m pip install -r requirements-dev.txt
```

### 3.4 Configure the backend

1. Copy the example settings file: `cp .env.example .env` (Windows: `copy .env.example .env`).
2. Open `backend/.env` and set:

| Variable | Required | Meaning |
| --- | --- | --- |
| `ORS_API_KEY` | Yes, for address search and routes | Your OpenRouteService key |
| `KOHA_ENV` | No (default `development`) | Environment name. Anything other than `development` or `test` makes `JWT_SECRET_KEY` mandatory |
| `JWT_SECRET_KEY` | Yes outside development | Token signing secret. Generate with `openssl rand -hex 32` |
| `DATABASE_URL` | No | Default is the SQLite file `backend/koharoute.db` |
| `CORS_ORIGINS` | No | Comma-separated browser origins allowed to call the API (default `http://localhost:5173`) |
| `SEED_ADMIN_PASSWORD`, `SEED_DRIVER_PASSWORD` | No, but recommended | Passwords for the demo accounts (at least 10 characters). Built-in demo defaults exist in `app/config.py`; do not use them anywhere public |
| `PHOTO_STORAGE_DIR` | No | Where uploaded photos are stored (default `backend/uploads/photos/`) |

Real environment variables override values in `.env`. **Never commit `.env`** (it is git-ignored).

### 3.5 Create and seed the database

From `backend/` with `KOHA-ROUTE` active:

```bash
python -m app.seed             # create tables and add anything missing (safe to repeat)
python -m app.seed --reset     # wipe everything, then seed (you must type "yes")
```

| Seeded item | On re-run |
| --- | --- |
| Settings (opening days, booking window, size presets, depot, ...) | Rewritten from `app/seed_data.py`. This is how a rule is changed in the MVP |
| Closed dates, categories, vehicles, demo bookings | Added only if missing; never overwritten |
| Users (1 Admin, 3 drivers) | Added only if missing; an existing account keeps its password |

Demo logins: `admin@koharoute.test`, and `driver1@koharoute.test` to `driver3@koharoute.test`, using
the passwords from `SEED_ADMIN_PASSWORD` / `SEED_DRIVER_PASSWORD`.

The demo data is 10 fictional bookings: six Approved on the next open day (160 kg and 730 L in
total, a realistic day to plan), three Pending and one Rejected. They have no photos.

### 3.6 Frontend setup

In a second terminal:

```bash
cd frontend
npm install
```

### 3.7 Start the system

```bash
# Terminal 1, from backend/ (KOHA-ROUTE active)
uvicorn app.main:app --reload        # API: http://localhost:8000/api/health, docs: /docs

# Terminal 2, from frontend/
npm run dev                          # App: http://localhost:5173
```

Vite proxies `/api` requests to port 8000, so start the backend first. Open
<http://localhost:5173>: the public start page is the donor booking form. Staff use `/login`.

### 3.8 Production build (optional)

```bash
cd frontend
npm run build                        # outputs frontend/dist/
```

Serve `frontend/dist/` with any static web server, run the API with a real `JWT_SECRET_KEY`, set
`KOHA_ENV=production`, and put the site's origin in `CORS_ORIGINS`.

### 3.9 Check that it works

- `http://localhost:8000/api/health` returns a healthy status.
- `http://localhost:5173/book` shows the booking form with open dates.
- Log in at `/login` as the demo Admin; you land on the booking review page.

## 4. Operating the system

**Donor: book a pickup (`/book`)**
1. Choose an available pickup date, item categories and a size, add an optional description and photos (JPG/PNG).
2. Type the pickup address and choose one of the suggestions (Auckland addresses only).
3. Enter name and contact number, accept the privacy notice, and submit.
4. Keep the booking reference shown on the confirmation page.

**Donor: track a booking (`/track`)** Enter the reference. You see the status and pickup date. Rejected
bookings show the reason; Missed bookings say the centre will contact you to reschedule.

**Admin: review bookings (`/admin`)**
1. Log in. The list shows Pending bookings; filter by status or pickup date.
2. Open a booking for contact details, description, photos, estimated load and a map preview.
3. Approve, or Reject with a reason. Approved or Missed bookings can be rescheduled to an open date.

**Admin: manage vehicles (`/admin/vehicles`)** Add or edit name, plate (6 letters/digits, stored in
upper case) and capacity (kg, m³). Deactivate instead of deleting. A vehicle with a Scheduled stop on a
Planned or In-progress route cannot be deactivated.

**Admin: plan routes (`/admin/routes`)**
1. Pick the date, then tick the active drivers and vehicles to use.
2. Press **Generate**. Approved bookings are sent to ORS once; the stop order, geometry, distance,
   duration and planned totals are saved. Bookings that do not fit stay Approved (unassigned).
3. Review the map and daily totals. Regenerating replaces an untouched plan; it is blocked once any
   stop is Completed or Missed.

**Driver: run a route (`/driver`)** Log in as a driver. Your route for the NZ-today date is shown with
the next Scheduled stop first. Open a stop for contact details, categories, description and photos;
use the navigation link; press Completed or Missed (a remark is required for Missed). Completed and
Missed stops cannot be changed by the driver; an Admin must reschedule Missed bookings.

**Maintenance**
- Change a business rule (opening days, size presets, depot): edit `backend/app/seed_data.py`, then re-run `python -m app.seed`.
- After a model change in development: `python -m app.seed --reset`.
- Manual ORS check: from `backend/`, run `python ../scripts/ors_optimization_spike.py`.

## 5. Testing and formatting

```bash
# backend/ (KOHA-ROUTE active)
python -m pytest
python -m black --check .            # drop --check to reformat

# frontend/
npm test
npm run format:check                 # use `npm run format` to fix
```

Backend tests use an in-memory SQLite database and a fake route planner, so they need no ORS key or network.

## 6. Project files and their purpose

### 6.1 Repository root

| File / folder | Purpose |
| --- | --- |
| `README.md` | This guide |
| `LICENSE` | Licence text (see section 10) |
| `environment.yml` | Conda environment `KOHA-ROUTE` (Python 3.11 + pip) |
| `.gitignore` | Keeps secrets (`.env`), databases, uploads, caches, `node_modules`, builds and zips out of git |
| `.editorconfig` | Shared editor settings (indentation, line endings) |
| `.vscode/settings.json` | VS Code: use conda for Python environments |
| `backend/` | FastAPI server, database and tests |
| `frontend/` | React web app |
| `scripts/` | Developer utilities |
| `docs/` | Reserved for project documents (currently empty) |

### 6.2 `backend/` (configuration and data)

| File | Purpose |
| --- | --- |
| `requirements.txt` / `requirements-dev.txt` | Runtime packages / runtime plus pytest, Ruff, Black |
| `pyproject.toml` | Black, Ruff and pytest settings |
| `.env.example` | Template for `.env` (keys, database, CORS, seed passwords) |
| `.env` | Your local secrets (not committed) |
| `koharoute.db` (+ `-wal`, `-shm`) | SQLite database created by the seed script (not committed) |
| `uploads/photos/` | Private, randomly named donor photos (not committed, never served publicly) |

### 6.3 `backend/app/` (application code)

| File | Purpose |
| --- | --- |
| `main.py` | Builds the FastAPI app: CORS, shared HTTP clients, registers every router |
| `config.py` | Environment-based deployment settings (database, CORS, ORS key, photo folder) |
| `database.py` | SQLAlchemy engine, sessions, SQLite settings, table creation |
| `security.py` | bcrypt password hashing; signed access tokens (JWT) |
| `timeutil.py` | The only place "today" is decided (New Zealand time) |
| `seed.py` | `python -m app.seed` logic: tables, settings, holidays, users, vehicles, demo bookings |
| `seed_data.py` | The seed data itself (settings, size presets, depot, NZ holidays 2026–27, categories, demo records) |

**`models/`** (one database table per file)

| File | Purpose |
| --- | --- |
| `booking.py` | Donor bookings and booking-category links |
| `category.py` | Item categories on the booking form |
| `closed_date.py` | Dates the centre does not collect (public holidays) |
| `photo.py` | Photo metadata (file lives on disk) |
| `route.py` / `route_stop.py` | Saved route plans per driver/vehicle/date, and their ordered stops |
| `setting.py` | Business rules as key/value rows |
| `user.py` | Admin and driver accounts |
| `vehicle.py` | Vehicles and capacities |
| `mixins.py`, `types.py` | Shared columns and custom column types |
| `__init__.py` | Registers all tables |

**`schemas/`** (request and response shapes)

| File | Purpose |
| --- | --- |
| `auth.py` | Login request/response |
| `bookings.py` | Donor booking, options, tracking |
| `admin_bookings.py` | Admin booking list/detail/actions |
| `vehicles.py` | Vehicle create/update/output |
| `routes.py` | Route planning options, generation and saved routes |
| `driver_routes.py` | Driver route and stop updates |

**`api/`** (HTTP endpoints; routers only translate HTTP to service calls)

| File | Purpose |
| --- | --- |
| `health.py` | `/api/health` status check |
| `auth.py` | Login and current-user endpoints |
| `deps.py` | Current-user and role-guard dependencies (Admin / driver) |
| `bookings.py` | Public options, address suggestions, booking creation and tracking |
| `admin_bookings.py` | Admin review, photos, approve / reject / reschedule |
| `admin_vehicles.py` | Admin vehicle management |
| `admin_routes.py` | Route options, totals, saved routes, generate |
| `driver_routes.py` | Driver routes, private photos, stop updates |

**`services/`** (business rules)

| File | Purpose |
| --- | --- |
| `auth_service.py` | Find user and check password |
| `login_throttle.py` | Limits repeated failed logins |
| `session_policy.py` | Session length from settings |
| `settings_service.py` | Reads/writes the business settings |
| `calendar_service.py` | Open-day rules (pure functions) |
| `booking_rules.py` | Booking validation and weight/volume estimates |
| `booking_service.py` | Creates a booking and its photos in one transaction |
| `booking_tracking_service.py` | Privacy-limited tracking lookup |
| `photo_service.py` | Validates photos and re-encodes them to strip metadata |
| `geocoding_service.py` | ORS address search with caching, rate limiting and signed selections |
| `admin_booking_service.py` | Admin review queries and status transitions |
| `vehicle_service.py` | Vehicle rules and validation |
| `route_planner.py` | ORS Optimization adapter plus a deterministic fake for tests |
| `route_generation_service.py` | Prepares jobs, calls the planner, saves/replaces routes |
| `driver_route_service.py` | Driver-only route reads and stop updates |

### 6.4 `backend/tests/` (pytest)

`conftest.py` provides shared fixtures. Test modules cover: `test_auth_api`, `test_auth_tokens`,
`test_security`, `test_login_throttle`, `test_session_policy` (login and sessions);
`test_booking_options_api`, `test_booking_rules`, `test_booking_tracking_api`, `test_photo_service`,
`test_geocoding_service` (donor booking); `test_admin_bookings_api`, `test_admin_vehicles_api`,
`test_driver_routes_api`, `test_route_stops_migration` (staff features and routes);
`test_models`, `test_database`, `test_seed`, `test_seed_data`, `test_settings_service`,
`test_calendar_service`, `test_timeutil`, `test_config`, `test_health` (foundation).

### 6.5 `frontend/`

| File | Purpose |
| --- | --- |
| `index.html` | Page shell; loads fonts and `/src/main.jsx` |
| `package.json` / `package-lock.json` | Dependencies and npm scripts (`dev`, `build`, `test`, `format`) |
| `vite.config.js` | Dev server on 5173, `/api` proxy to port 8000, Vitest (jsdom) |
| `.prettierrc.json` | Prettier rules |
| `dist/` | Build output from `npm run build` (generated) |

**`frontend/src/`**

| File | Purpose |
| --- | --- |
| `main.jsx` | App entry: theme, router, auth provider, public routes |
| `theme.js` | Dark theme, brand colours, status and route colours |
| `routes/staffRoutes.jsx` | Login and role-protected Admin/driver routes |
| `auth/AuthContext.jsx`, `tokenStorage.js`, `roleHome.js`, `RequireRole.jsx` | Login state, token storage, role home page, route guard |
| `api/http.js` | Shared fetch wrapper (auth header, errors) |
| `api/adminBookings.js`, `adminVehicles.js`, `adminRoutes.js`, `driverRoutes.js`, `health.js` | One small client per backend resource |
| `hooks/usePolling.js` | Repeated refresh of live data |
| `hooks/useNzToday.js` | Today's date in New Zealand time |
| `utils/volume.js` | Litres to m³ formatting |
| `pages/BookPickup.jsx` | Donor booking form |
| `pages/TrackBooking.jsx` | Donor tracking page |
| `pages/LoginPage.jsx` | Staff login |
| `pages/AdminBookingsPage.jsx` | Admin booking review |
| `pages/AdminVehiclesPage.jsx` | Vehicle management |
| `pages/AdminRoutesPage.jsx` | Route planning, map and totals |
| `pages/DriverRoutePage.jsx` | Driver route, stops and updates |
| `pages/StaffHomePlaceholder.jsx` | Placeholder staff home (not routed) |
| `components/ScreenBackdrop.jsx` | Decorative page background |
| `*.test.jsx` / `*.test.js` | Vitest tests beside the code they test |


## 7. API summary

Interactive documentation is at <http://localhost:8000/docs> when the backend runs.

| Area | Endpoints | Access |
| --- | --- | --- |
| Health | `GET /api/health` | Public |
| Auth | `POST /api/auth/login`, `GET /api/auth/me` | Public / signed in |
| Donor | `GET /api/bookings/options`, `GET /api/bookings/address-suggestions`, `POST /api/bookings`, `GET /api/bookings/track/{reference}` | Public |
| Admin bookings | `GET /api/admin/bookings`, `GET /{id}`, `GET /{id}/photos/{photo_id}`, `POST /{id}/approve`, `/reject`, `/reschedule` | Admin |
| Admin vehicles | `GET/POST /api/admin/vehicles`, `PUT /{id}`, `PATCH /{id}/deactivate` | Admin |
| Admin routes | `GET /api/admin/routes/options`, `GET /api/admin/routes`, `GET /totals`, `POST /generate` | Admin |
| Driver | `GET /api/driver/routes`, `PATCH /{route_id}/stops/{booking_id}`, `GET /{route_id}/stops/{booking_id}/photos/{photo_id}` | Driver (own routes only) |

## 8. Data model

| Table | Holds |
| --- | --- |
| `settings` | Business rules as key/value rows (JSON values) |
| `closed_dates` | NZ public holidays that fall on weekdays, 2026 and 2027 |
| `categories` | Item categories on the booking form |
| `users` | Admin and drivers (role checked by the database) |
| `vehicles` | Capacity in whole kg and whole litres |
| `bookings` | Donor requests, estimated kg and litres, one of the six statuses |
| `booking_categories` | Which categories a booking has |
| `photos` | Photo metadata (random stored name; file on disk) |
| `routes` | Saved driver/vehicle plans, geometry, distance/duration, planned estimates |
| `route_stops` | ORS-ordered booking stops and lifecycle status |

Security and privacy notes: staff routes are protected server-side by role; photos are re-encoded to
remove metadata and are served only through authenticated endpoints; tracking never reveals the
street address, name, phone or photos.

## 9. Coding standards

| Standard | Where it is shown |
| --- | --- |
| Modularity and encapsulation | `config.py` (settings only), `database.py` (all SQLite details), `timeutil.py` (the only place "today" is decided); routers call services; `settings_service` is the only reader of setting rows; frontend split into `api/`, `hooks/`, `pages/` |
| Performance | Cached config read, one session per request, SQLite WAL, cancelled stale requests (`AbortController`), database indexes, `selectin` loading, one-query settings read, single-transaction seed, ORS client reuse with caching and rate limiting |
| Commenting and documentation | Google-style docstrings enforced by Ruff rule set `D`; comments explain why; JSDoc on frontend helpers; this README |
| Indentation and formatting | Black and Ruff (4 spaces, 100 columns); Prettier (2 spaces, single quotes); `.editorconfig` |
| Naming conventions | `snake_case` Python, `PascalCase` classes/components, `UPPER_SNAKE_CASE` constants, `camelCase` JavaScript |

## 10. Licence

KohaRoute is released under the **MIT Licence**. The full text is in the `LICENSE` file. In short:
you may use, copy, modify, merge, publish, distribute and sell the software, provided the copyright
notice and licence text are kept in all copies. The software is provided "as is", without warranty
of any kind, and the authors are not liable for any claim or damages arising from its use.

Third-party components keep their own licences (FastAPI, SQLAlchemy, React, Material UI, Leaflet and
others). Map and address data come from OpenRouteService and OpenStreetMap contributors and are subject
to their terms and attribution requirements. Public holiday dates are taken from Employment New Zealand.


**Security reminders**
1. Demo accounts use built-in default passwords unless `SEED_*_PASSWORD` is set, and a development-only JWT secret is used when `KOHA_ENV` is `development`. Change both before any public deployment.
2. A local `.env`, database and uploaded photos can exist in a working copy. They are git-ignored; do not share them or include them in a zip.

## 11. Credits

**Developers (Team Koha)**

| Name | GitHub |
| --- | --- |
| Seyoung Oh | osy0602 |
| Chaw Theingi | chawtg |
| keensalino14 | keensalino14 |
| banggawandaniel-blip | banggawandaniel-blip |

**Client:** Te Manawa Community Centre.

**Acknowledgements:** [OpenRouteService](https://openrouteservice.org) and
[OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (address search, routing, map data);
[Employment New Zealand](https://www.employment.govt.nz/leave-and-holidays/public-holidays/) (public holiday dates);


# KohaRoute

Pickup booking and route planning for Auckland Community Centre by Team Koha.

It contains an empty but working backend, frontend and test
setup. 

## Folder layout

```
koharoute/
  environment.yml        conda environment (KOHA-ROUTE, Python 3.11)
  backend/
    app/                 FastAPI code: config, database, NZ time helper, routers
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
| Modularity and encapsulation | `config.py` (settings only), `database.py` (all SQLite details), `timeutil.py` (the only place "today" is decided), `api/health.py` (one router per feature); frontend split into `api/`, `hooks/`, `pages/` |
| Performance | One cached config read (`lru_cache`); one session per request, always closed; SQLite write-ahead logging; shared in-memory connection in tests; `AbortController` cancels stale requests |
| Commenting and documentation | Google-style docstrings on every public function (enforced by Ruff rule set `D`); comments explain why (for example, why `date.today()` is banned); JSDoc on the frontend helpers; this README |
| Indentation and formatting | Black and Ruff (4 spaces, 100 columns) via `pyproject.toml`; Prettier (2 spaces, single quotes) via `.prettierrc.json`; `.editorconfig` for every editor |
| Naming conventions | `snake_case` functions and files, `PascalCase` classes and React components, `UPPER_SNAKE_CASE` constants, `camelCase` JavaScript; names follow the spec vocabulary |

## Known limits in Part 0

- The login, bookings and routes do not exist yet.
- `nz_today` in the health report is there to prove NZ time works end to end.

# House of X

A small local catalog of Jonathan Hickman's X-Men, weighted toward the work after *House of X* (2019). Python API (FastAPI), React UI (Vite).

"House of X" is this demo's name, not a claim of ownership. All titles, credits, descriptions, dates and images come from the Marvel developer API and are displayed as returned. Nothing here is a summary or retelling of the stories.

## Marvel attribution

Every page that renders Marvel data shows the `attributionText` the API returns, beside the site name (header and footer). Marvel's data is fetched server-side only; the private key never reaches the browser, logs, or git. Responses are cached in SQLite (`apps/api/.cache/`, git-ignored) with a 24 hour TTL (`CACHE_TTL_SECONDS` in `apps/api/app/config.py`). Check the current Marvel developer terms and change that constant if they differ. Do not publish a mirror of the catalog.

## Demo mode vs real Marvel

Marvel's public API is retired, so the default is **demo mode**: a small local mock gateway (`apps/api/mock_marvel/`) serves Marvel-shaped JSON from `apps/api/fixtures/marvel_sample.json`. **That fixture is hand-authored sample data, not Marvel's.** It carries its own attribution line saying so, and it includes edge cases (a non-writer credit, a missing description, a missing image, an out-of-window issue, an unresolvable series). The catalog code path is identical in both modes; only `MARVEL_BASE_URL` changes. The mock checks `ts`/`apikey`/`hash` like Marvel did, using throwaway demo keys.

Run it as a separate process: `scripts/run-mock.sh` (or `scripts/run-mock.ps1`), port 8001. To use a real Marvel-compatible source if one returns, empty `MARVEL_BASE_URL` (default `https://gateway.marvel.com/v1/public`) and set your own keys.

## Environment variables

Copy `.env.example` to `.env` (the setup scripts do this) and fill in:

- `MARVEL_BASE_URL` (optional; demo default points at the mock)
- `MARVEL_PUBLIC_KEY`
- `MARVEL_PRIVATE_KEY`

Catalog routes return 503 with a plain message if either is missing; `/api/health` works without them.
The web app reads `VITE_API_BASE` (default `http://localhost:8000`; see `apps/web/.env.example`).

## Setup (Python 3.12, Node 22)

- Linux/macOS: `scripts/setup.sh`
- Windows: `scripts/setup.ps1`

Both create `.venv`, install the API with dev extras, and run `npm ci` in `apps/web`.

## Run

```
# Mock Marvel gateway (demo mode)
scripts/run-mock.sh

# API (from the repo root)
.venv/bin/uvicorn app.main:app --app-dir apps/api --port 8000   # Windows: .venv\Scripts\uvicorn

# Web
cd apps/web && npm run dev
```

Tests: `cd apps/api && ../../.venv/bin/pytest` and `cd apps/web && npm test`.

## The shelf rule

- The creator is resolved from `/creators?lastName=Hickman&firstName=Jonathan`. If more than one match returns, the API stops (409) and reports the names.
- A comic is on the shelf only when that creator is credited as **writer**.
- Series are resolved by title and start year; any the API does not return are skipped. Prior shelf: House of X (2019), Powers of X (2019). Main shelf: X-Men (2019), Giant-Size X-Men (2020), Inferno (2021).
- The date window runs from the on-sale date of the House of X series to the on-sale date of the last Hickman-written issue in those series. Comics from other series appear only if they fall in that window and credit Hickman as writer; they are labelled as API results, not a complete run.
- Characters are derived from the in-scope comics, plus a seed list resolved by name. Character pages list only in-scope comics.

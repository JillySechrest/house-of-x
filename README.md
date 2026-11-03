# House of X

A small local catalog of Jonathan Hickman's X-Men, weighted toward the work after *House of X* (2019). Python API (FastAPI), React UI (Vite).

Agents: start with [AGENTS.md](AGENTS.md), then read [PLAN.md](PLAN.md). Future harness work is in [docs/harness-roadmap.md](docs/harness-roadmap.md), with executable work items in [docs/harness-backlog.json](docs/harness-backlog.json).

"House of X" is this demo's name, not a claim of ownership. **Marvel's public API is retired.** Catalog and roster data are committed JSON fixtures, not a live Marvel feed. Do not add a `gateway.marvel.com` client.

## Data and attribution

Canonical files:

- `apps/api/fixtures/krakoan_roster.json` — factions/characters, loaded in-process. Labelled as supplied data, not Marvel.
- `apps/api/fixtures/marvel_sample.json` — hand-authored Marvel-*shaped* sample catalog (not Marvel's). Attribution line says so.

Every page that renders catalog data shows that sample `attributionText` beside the site name (header and footer). Do not publish a mirror presented as Marvel.

## Catalog shim (temporary)

Catalog routes still talk HTTP to a local mock (`apps/api/mock_marvel/`) that serves `marvel_sample.json` on port 8001. The mock checks `ts`/`apikey`/`hash` with throwaway demo keys so the old client code still runs. That is a shim to retire (load JSON in-process like the roster). Do not point `MARVEL_BASE_URL` at Marvel.

Run the mock: `scripts/run-mock.sh` (or `scripts/run-mock.ps1`). The fixture includes edge cases (a non-writer credit, a missing description, a missing image, an out-of-window issue, an unresolvable series).

## Roster data

`apps/api/fixtures/krakoan_roster.json` is a roster of factions and characters supplied with the project (not from Marvel). `GET /api/roster` serves it without a Marvel call or keys; the UI shows it at `/roster` and on matching character pages, labelled as supplied data. Entries match Marvel characters by alias or name (Kate/Kitty Pryde are treated alike). The file's `total_characters` is recomputed from the factions on load. Cleanup versus the pasted source: stray text removed and `&amp;` unescaped.

## Environment variables

Copy `.env.example` to `.env` (the setup scripts do this). Demo `MARVEL_*` values are throwaways for the mock shim only — there are no real Marvel keys. Catalog routes still return 503 if those env vars are missing; `/api/health` and `/api/roster` work without them.
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

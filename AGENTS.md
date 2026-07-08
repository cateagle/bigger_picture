# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project

A browser-playable citizen-science game that crowdsources ground-truth annotations for a marine-image dataset (for training image-registration/matching ML models). Three game modes, each a filter/refinement stage over the same data:

1. **Finding Overlap** (`/overlap`, frontend `OverlapGame`) — binary "do these two images overlap?" vote. Cheap funnel.
2. **Annotating** (`/annotate`, frontend `AnnotateGame`) — click matched point pairs between two images known to overlap. This is the ground-truth signal; conceptually the multiplayer version of the point-picking workflow in `compute_homographies.py` (the original single-user OpenCV prototype at the repo root — homography/fundamental-matrix estimation from `pts1`/`pts2` is meant to move server-side eventually).
3. **Verification** (`/verify`, frontend `VerifyGame`) — peer review of another player's Stage 2 annotation.

Stages 1 and 2 (Overlap, Annotating) are wired to the real backend end-to-end, including fetching the next candidate/pair to work on (`GET /api/v1/annotate/candidate/next/{dive_uuid}`, `GET /api/v1/annotate/points/next/{dive_uuid}`; the frontend resolves a region to a dive_uuid via `GET /api/v1/annotate/dives?region=...`). Only Stage 3 (Verification) is still playable against mocked data (`frontend/src/api/verifyApi.ts`) — the backend has no review-queue endpoint yet. Check `frontend/src/api/*Api.ts` for which calls are mocked vs. real before assuming an endpoint exists.

Repo layout: `frontend/` (React SPA), `backend/` (FastAPI + SQLite), `docker-compose.yml` (runs both locally), `compute_homographies.py` (standalone prototype, unrelated to the two services' build/test setup).

## Commands

### Backend (from `backend/`, via `devenv shell --`)

```sh
devenv shell -- uvicorn src.main:app --reload      # run the API (applies migrations on startup)
devenv shell -- python -m src.main                 # alternative entrypoint
devenv shell -- python -m pytest                   # full test suite
devenv shell -- python -m pytest tests/test_auth.py                      # one file
devenv shell -- python -m pytest tests/test_auth.py::test_signup_sets_cookie  # one test
devenv shell -- python -m src.bootstrap_admin --username admin           # create first admin (role can't self-elevate)
```

The dev shell (Nix `devenv`) provides Python 3.12 + `uv`-synced deps; there's no plain venv workflow — always prefix backend commands with `devenv shell --`.

### Frontend (from `frontend/`)

```sh
npm install
npm run dev       # vite dev server, http://localhost:5173
npm run build     # tsc -b && vite build
npm run lint      # oxlint
npm run preview
```

No frontend test runner is configured (no test script/framework in `package.json`).

### Whole stack

```sh
docker compose up   # backend on :8000, frontend on :5173 with hot reload
```

## Backend architecture

- **Entrypoint**: `src/main.py:create_app()` wires the migration runner, SQLAlchemy engine/session factory (stashed on `app.state`), `AuthMiddleware`, CORS, the `/assets` static mount, and the `/api` router. Both `uvicorn.run` and the pytest `app` fixture (`tests/conftest.py`) go through this one factory, parameterized by `database_path`.
- **Auth model**: no passwords. `POST /api/v1/auth/signup {"username"}` creates an `annotator` and sets an httponly `session_uuid` cookie holding the user's raw uuid — the cookie *is* the credential, there's no separate login/session table. `src/config.py` handles uuid<->cookie hex encoding.
- **Access control**: a single `AuthMiddleware` (`src/api/middleware/auth_middleware.py`) resolves the user from the cookie on *every* request (storing it on `request.state.user`, `None` if absent/invalid) and enforces role minimums by URL prefix: `/api/v1/auth/*` public, `/api/v1/annotate/*` any authenticated role, `/api/v1/dataset/*` scientist+, `/api/v1/admin/*` admin only, anything else under `/api/v1` fails closed to admin-only. Roles are hierarchical (`Role`/`ROLE_RANK` in `src/constants.py`): `annotator` < `scientist` < `admin`. `expert_level` on `users` is an unrelated annotation-weight field, not a permission level. 401 = unauthenticated, 403 = authenticated but insufficient role.
- **Migrations**: hand-written sequential `.sql` files in `src/migrations/` (e.g. `0001_initial_schema.sql`), applied automatically on app startup by `src/migrations/runner.py`, which tracks applied filenames in a `schema_migrations` table and wraps each file in `BEGIN`/`COMMIT` itself — migration files must not include their own transaction or `PRAGMA foreign_keys` statements. SQLAlchemy models under `src/schema/` mirror the SQL by hand (not generated from it) and must be updated alongside any new migration.
- **Status lookup tables**: `image_statuses`, `pair_statuses`, `candidate_statuses`, `annotation_statuses` are fixed enums seeded once via `INSERT OR IGNORE`, never modified at runtime, and have no CRUD endpoint. The Python-side source of truth is the matching `StrEnum` + int-mapping dict pair in `src/constants.py`, not the DB rows — adding a status value means a new migration *and* new `constants.py` entries together. `tests/test_status_enum_sync.py` guards the two from drifting apart.
- **SQLite pragmas** are split by lifetime: `journal_mode=WAL` and `auto_vacuum=FULL` are set once by the migration runner (`src/migrations/runner.py`) because they're persisted in the file header; `foreign_keys=ON`, `busy_timeout`, `synchronous=NORMAL` are set per-connection in `src/db.py`'s `connect` event listener because SQLite resets them every connection.
- **Layout**: `src/api/v1/{auth,annotate,dataset,admin}/` mirror the middleware's role prefixes. `src/models/` = Pydantic request/response schemas; `src/schema/` = SQLAlchemy ORM models; `src/services/` = shared logic (asset path resolution, lookup helpers) used across routers.
- **Assets**: images are served from `ASSETS_DIR` (default `backend/assets/`) at `/assets`, public regardless of the `/api/v1` role rules.
- **Adding a new dataset resource/controller**: follow [`backend/docs/adding-a-controller.md`](backend/docs/adding-a-controller.md) — a step-by-step checklist (migration, SQLAlchemy schema, Pydantic models, router, wiring, tests) distilled from the existing `regions`/`cameras`/`dives` controllers.

## Frontend architecture

- Not React Router — `App.tsx` holds `screen` state (`'home' | 'overlap' | 'annotate' | 'verify'`) and switches components directly; there's no URL-based routing.
- Auth state (`User | null | undefined`) also lives in `App.tsx`: `undefined` = still checking `/auth/me`, `null` = show `LoginScreen`, otherwise render the home/game screens.
- `src/api/` is one file per backend domain (`authApi`, `annotationApi`, `overlapApi`, `datasetApi`, `adminApi`, `diveApi`, `regionApi`) plus `verifyApi`, which is currently mocked (see `mockDelay.ts`) since the backend has no review-queue endpoint yet — don't assume calls in that file hit the real API.
- `src/api/client.ts`'s `apiFetch` is the single fetch wrapper: always sends cookies (`credentials: 'include'`, since the auth cookie is httponly and can't be attached manually), throws `ApiError` (with FastAPI's `{"detail": ...}` shape) on non-2xx.
- `VITE_API_BASE_URL` (from `.env`, copy from `.env.example`) points the frontend at the backend; defaults to `http://localhost:8000`.

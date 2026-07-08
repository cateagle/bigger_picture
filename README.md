# Bigger Picture

A browser-playable citizen-science game that crowdsources ground-truth annotations for a dataset of marine images, so the results can be used to train machine learning models (e.g. for image registration / matching).

Instead of paying experts to manually annotate overlapping image pairs, we turn the annotation process into a short, low-friction game. Anyone can play a round in their browser, and each round produces a small piece of labeled data (an overlap decision, a set of matched points, or a verification vote). Aggregated across many players, these micro-contributions add up to a full annotated dataset.

This repository is split into a `frontend` (React/TypeScript SPA) and a `backend` (FastAPI + SQLite API and persistence). It can be run as a single production container, as a two-container Docker Compose dev setup, or directly on the host with npm and Python — see ["Running the stack"](#running-the-stack).

## Background

`compute_homographies.py` in the repo root is the original, single-user prototype this project grows out of: a local OpenCV tool where a person clicks matching points between two images, guided by an epipolar line once enough correspondences exist to estimate a fundamental matrix. That workflow — "pick a point on the left image, find the same point on the right image" — is exactly what stage 2 of the game (see below) turns into a multiplayer, browser-based, gamified task. The homography/fundamental-matrix computation itself will move server-side, informed by the point pairs the game collects.

## Concept: the three stages

The dataset annotation pipeline is broken into three distinct game modes. Each produces a different kind of signal, and later stages consume/validate the output of earlier stages.

### Stage 1 — Finding Overlap

**Goal:** cheaply filter which image pairs are worth annotating at all.

- The player is shown two marine images side by side.
- The only decision: **do these two images overlap (show at least partially the same physical scene), or not?**
- A simple binary choice (e.g. "Overlap" / "No overlap"), answerable in a few seconds.
- This is the fastest, lowest-cognitive-load stage — designed to have the highest throughput and act as a funnel: only pairs a sufficient number of players agree overlap are promoted to Stage 2.

### Stage 2 — Annotating

**Goal:** produce point correspondences between two images that are known to overlap.

- The player is shown two overlapping images (as identified in Stage 1).
- The task: click a point in image A, then click the corresponding physical point in image B (the same rock, coral edge, tag, distinctive feature, etc.).
- Repeated for several points per pair.
- These correspondence pairs are exactly the `pts1`/`pts2` input that `compute_homographies.py` currently collects by hand — the game collects them from many players instead of one operator. As in the prototype, correspondences can be used to fit a fundamental matrix / homography between the two images; once a rough model exists, later clicks in a session could be guided by an epipolar line to speed up and improve accuracy, the same guided mode already implemented in the prototype script.
- Output: a set of "connected dots" (point pairs) per image pair, which is the ground-truth training signal for image-matching ML models.

### Stage 3 — Verification

**Goal:** quality-control the annotations produced in Stage 2 without relying on a single trusted expert.

- The player is shown an already-annotated image pair (annotated by a *different* player in Stage 2), with the connected points overlaid.
- The task: judge whether the annotation looks correct, and reject/flag it if not.
- Agreement across multiple verifiers determines whether an annotation is accepted into the final training dataset, sent back for re-annotation, or discarded.

### Why three stages

Splitting the pipeline this way keeps every individual task short and simple (good for a casual, gamified experience) while building in redundancy and cross-checking (overlap has to be agreed on before annotation is even offered; annotations get reviewed by peers rather than trusted blindly) — a standard citizen-science pattern for producing a reliable dataset out of noisy, unpaid, non-expert contributions.

## Gamification

Not fully designed yet, but the intended direction:

- Points/score per completed round, weighted by stage (annotation > verification > overlap, reflecting effort).
- Streaks / accuracy bonuses when a player's answers agree with the eventual consensus.
- Progress and leaderboards to encourage return visits.
- Possibly unlockable stages: e.g. new players start on Stage 1/3 (fast, low-error-risk tasks) and unlock Stage 2 (annotation) once they've demonstrated reliability.

## Architecture

```
bigger_picture/
├── Dockerfile             # single-container production build (frontend embedded in backend)
├── docker-compose.yml     # orchestrates the two-container dev stack
├── frontend/              # React + TypeScript SPA — the game itself
├── backend/               # FastAPI + SQLite API, auth, and persistence
├── compute_homographies.py  # original single-user annotation prototype (OpenCV)
├── scripts/              # dataset ingestion & seeding CLIs (see "Dataset ingestion")
└── README.md
```

- **Frontend**: a single-page React app. Renders the three game modes, an admin area, and a team/about screen, and collects player input. All three stages talk to the real backend end-to-end, including fetching the next thing to work on (candidate pair, image pair, or pending review).
- **Backend**: serves auth (self-service signup via a session cookie, no password), dataset CRUD (regions, dives, images, pairs), and the overlap/annotation/verification queues and submission endpoints for all three stages. Still to come: scoring/consensus and gamification mechanics. See [`backend/README.md`](./backend/README.md) for details.
- **Local deployment**: `docker-compose.yml` runs both the `frontend` and `backend` services so the whole stack can be started with `docker compose up`.
- **Production deployment**: a root-level `Dockerfile` builds the frontend and embeds the static output directly into the FastAPI backend image, so the whole app ships as one container running only `uvicorn`.

## Running the stack

Three ways to run this, depending on what you're doing:

### Production: single container

The root [`Dockerfile`](./Dockerfile) multi-stage builds the frontend, copies the static build into the backend image as the last step, and serves it directly from FastAPI — no Node, no Vite dev server, no separate frontend process in the final image.

```sh
docker build -t bigger-picture -f Dockerfile .
docker run --rm -p 8000:8000 bigger-picture
```

Open http://localhost:8000 — the frontend is served at `/` by the same process as the API, so requests are same-origin and CORS doesn't come into play.

### Local development: Docker Compose

```sh
docker compose up
```

Runs `frontend/Dockerfile` and `backend/Dockerfile` as two containers with your local checkout bind-mounted in: frontend dev server with hot reload on http://localhost:5173, backend on http://localhost:8000. This is the day-to-day two-origin dev setup (frontend calls the backend via `VITE_API_BASE_URL`, backend allows that origin via CORS).

### Local development: without Docker

Needs Node 22+ and Python 3.12+, plus [uv](https://docs.astral.sh/uv/) for the backend. If you use [devenv](https://devenv.sh) (this repo has a `devenv.nix`), `devenv shell` provisions all of that for you — prefix any command below with `devenv shell --`. Devenv is entirely optional; the commands are identical either way, just installed differently.

**Backend** (from `backend/`):

```sh
uv sync
uv run uvicorn src.main:app --reload
```

**Frontend** (from `frontend/`, separate terminal):

```sh
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm install
npm run dev
```

Same two-origin setup as Docker Compose (`:5173` / `:8000`), just running directly on the host instead of in containers.

To try the *embedded* build locally — same-origin, no Vite dev server, what the production container does — without needing Docker at all:

```sh
cd frontend && npm run build:embedded   # writes frontend/dist, built for same-origin use
cd ../backend && uv run uvicorn src.main:app
```

Open http://localhost:8000. The backend picks up `frontend/dist` automatically (no env vars needed) and serves it the same way the production container does.

See [`backend/README.md`](./backend/README.md) for backend-specific details (auth model, config, migrations).

## Frontend

- **Stack**: [Vite](https://vite.dev/) + [React](https://react.dev/) + TypeScript.
- **Location**: [`frontend/`](./frontend).
- All three game screens (Finding Overlap, Annotating, Verification) are implemented and playable from the home screen's stage picker.
- The account bar (top of the home/region-select screens) also links to an admin area (regions/labels/users CRUD, restricted to non-`annotator` roles) and a `Team` page listing project contributors.

### Running the frontend

See ["Running the stack"](#running-the-stack) above for all three ways to run the frontend (production container, Docker Compose, or directly with npm) — in every case the backend needs to be running too; all three stages fetch real regions/dives/candidates/pairs/reviews from it, nothing in the frontend works against mocked data.

## Dataset ingestion (`scripts/`)

Command-line tools for getting marine images and their pairs into the backend. They drive the REST API (so they respect auth and validation) and authenticate as a `scientist`/`admin` user — the Docker Compose setup seeds an `admin` user on startup (`SEED_ADMIN_USERNAME`), which the scripts log in as by default.

- **`sort_images.py`** — scans an image folder, assigns each image a uuid, and pairs each image with its next N neighbours. Writes `images.csv` (`filename,uuid`) and `image_pairs.csv` (uuid pairs); re-runs reuse existing uuids so they stay stable.
- **`upload_dataset.py`** — uploads the images and creates the pairs for a chosen dive from those two CSVs, and with `--publish` flips them to `open` so they become available for annotation. Idempotent: a local `*.state.json` ledger lets reruns skip work already done.
- **`seed_examples.py`** — one-shot seeding of the bundled example datasets under `scripts/example_data/` (`dive1`, `north_sea`): ensures each dive and its region exist, prepares the CSVs, uploads, and publishes.
- **`reset.py`** — deletes the SQLite database and all `*.state.json` ledgers for a clean slate.

Quick start (with the stack running via `docker compose up`):

```sh
python3 scripts/seed_examples.py             # seed dive1 + north_sea
python3 scripts/seed_examples.py north_sea   # just one dataset
```

## Status

- ✅ Concept and three-stage game design documented (this README).
- ✅ Repository split into `frontend`/`backend`, Docker Compose deployment for both services.
- ✅ Frontend: all three game screens built, with routing between them from the home screen, plus an admin area and a team page.
- ✅ Frontend API client wired to the real backend (auth, dataset summary, labels, regions, dives) with a `VITE_API_BASE_URL` env var for the backend location.
- ✅ Backend: FastAPI + SQLite, with auth, dataset, and admin endpoints.
- ✅ All three stages (Finding Overlap, Annotating, Verification) wired end-to-end, including fetching the next thing to work on for each.
- ✅ Dataset ingestion: `scripts/` CLIs and a bulk zip-upload endpoint for getting marine images and pairs into the backend.
- ⬜ Gamification mechanics (scoring, consensus, leaderboards) — design only, not implemented.

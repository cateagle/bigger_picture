# Bigger Picture

A browser-playable citizen-science game that crowdsources ground-truth annotations for a dataset of marine images, so the results can be used to train machine learning models (e.g. for image registration / matching).

Instead of paying experts to manually annotate overlapping image pairs, we turn the annotation process into a short, low-friction game. Anyone can play a round in their browser, and each round produces a small piece of labeled data (an overlap decision, a set of matched points, or a verification vote). Aggregated across many players, these micro-contributions add up to a full annotated dataset.

This repository is split into a `frontend` (this is where active development currently happens) and a `backend` (API + persistence, not built yet). The two are wired together with Docker Compose so the whole stack can be run locally with one command.

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
├── docker-compose.yml     # orchestrates the stack for local deployment
├── frontend/              # React + TypeScript SPA — the game itself
├── backend/               # not yet created — API, scoring, dataset/image storage
├── compute_homographies.py  # original single-user annotation prototype (OpenCV)
└── README.md
```

- **Frontend**: a single-page React app. Renders the three game modes, collects player input, and talks to the backend over HTTP (API shape TBD once the backend exists). This is the current focus of development.
- **Backend** (planned, not implemented): serves image pairs to annotate/verify, receives round results, tracks scoring/consensus, and persists the growing annotation dataset. Likely responsibilities include picking which image pair to serve next (prioritizing pairs that need more overlap votes, more annotations, or more verification), and eventually running the homography/fundamental-matrix fitting that `compute_homographies.py` does locally today.
- **Local deployment**: `docker-compose.yml` wires the services together so the whole stack (as it grows) can be started with `docker compose up`. Only the frontend is defined so far; the backend service will be added once its stack is decided.

## Frontend

- **Stack**: [Vite](https://vite.dev/) + [React](https://react.dev/) + TypeScript.
- **Location**: [`frontend/`](./frontend).
- Currently an empty scaffold (default landing page only) — the three game screens have not been built yet.

### Running the frontend

With Docker Compose (recommended, matches how the whole project will eventually run):

```sh
docker compose up frontend
```

The dev server is then available at http://localhost:5173, with hot reload against your local `frontend/` checkout.

Without Docker, directly with Node (22+ recommended):

```sh
cd frontend
npm install
npm run dev
```

## Status

- ✅ Concept and three-stage game design documented (this README).
- ✅ Repository split into `frontend`/`backend`, Docker Compose scaffold for local deployment.
- ✅ Empty React/TypeScript frontend scaffold.
- ⬜ Frontend: build the three game screens, routing between them, and API client.
- ⬜ Backend: not started (framework/stack not yet decided).
- ⬜ Dataset ingestion pipeline for the marine images themselves.
- ⬜ Gamification mechanics (scoring, consensus, leaderboards) — design only, not implemented.

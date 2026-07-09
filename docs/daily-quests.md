# Daily quests

This page explains how the daily quest set is chosen, how a quest's progress is measured, and how claiming a quest grants exp.

The relevant code lives in [`backend/src/services/quests.py`](../backend/src/services/quests.py) (catalog, day window, selection, progress counting), [`backend/src/api/v1/annotate/quests.py`](../backend/src/api/v1/annotate/quests.py) (the two endpoints), and [`backend/src/config.py`](../backend/src/config.py) (the tunables).

## Step 1: nothing about a quest's progress is stored

A quest is a `QuestTemplate` (`key`, `title`, `description`, `metric`, `target`, `reward_exp`) drawn from a fixed, hardcoded `CATALOG` in `quests.py`. There is no `quests` table. Likewise there is no per-user "progress" row: every time progress is requested, it's computed on the spot as a `COUNT(*)` (or `COUNT(DISTINCT pair_id)`) over the existing `candidate_annotations` / `point_annotations` tables, filtered to that quest's `metric` and today's window. This mirrors how `stats.py` computes the "My Stats" screen's counters — quests just add a metric-name indirection and a day-window filter on top of the same tables.

The only thing that *is* persisted is a claim (Step 4) — a small row recording "this user already collected this quest's reward today."

## Step 2: progress only counts confirmed work

Every metric filters on `status_id == ANNOTATION_APPROVED` and windows on `reviewed_at`, not `created_at`:

| Metric                       | Source table          | Filter (in addition to the day window)                              |
|-------------------------------|------------------------|-----------------------------------------------------------------------|
| `pairs_confirmed`             | `candidate_annotations`| `created_by = user`, approved                                         |
| `overlaps_confirmed`          | `candidate_annotations`| `created_by = user`, approved, `no_overlap = false`                    |
| `points_confirmed`            | `point_annotations`    | `created_by = user`, approved                                         |
| `pairs_annotated_confirmed`   | `point_annotations`    | `created_by = user`, approved, `COUNT(DISTINCT pair_id)`               |
| `verifications`               | both tables            | `reviewed_by = user` (a review is the reviewer's own confirmed action) |

This is a deliberate design choice, not an oversight: the existing exp system ([`docs/candidate-auto-review.md`](./candidate-auto-review.md)) only ever grants exp for reviewed-and-approved work, never for a raw submission. Quest progress follows the same rule so a quest can never be completed — and its exp reward never claimed — for work that hasn't actually been confirmed yet. A player who submits 50 points today but has none reviewed yet sees `0/50` progress, not `50/50`; the count only climbs as review decisions land, whether by another player's manual review or by [candidate auto-review](./candidate-auto-review.md) firing.

## Step 3: the daily set is the same for every player

"Today" is a local-midnight-to-midnight window in `config.QUEST_TIMEZONE` (default `Europe/Berlin`), computed by `day_window(now_ms)`. Its `start_ms` is a calendar boundary (`+1 day`, not `+24h`, so it stays correct across DST changes) and doubles as the seed for that day's quest selection:

```
rng = random.Random(day_start_ms)
quests = rng.sample(CATALOG, k=QUEST_COUNT_PER_DAY)
rng.shuffle(quests)
```

Because the seed is the day's start timestamp and nothing else — `user.id` is deliberately never mixed in — every player who asks `GET /api/v1/annotate/quests/me` on the same calendar day gets the same quests, in the same order. The set rotates automatically at local midnight, with no scheduled job or stored "today's quests" row: the next request after midnight simply computes a new `day_start_ms`, which produces a new (deterministically different) sample.

## Step 4: claiming

`POST /api/v1/annotate/quests/{quest_key}/claim`:

1. Looks up the key in `CATALOG_BY_KEY` and checks it's actually part of *today's* selection — 404 otherwise (guards against claiming a stale key from a previous day, or one that never existed).
2. Recomputes progress for that metric and requires `progress >= target` — 409 if not yet complete.
3. Inserts a `quest_claims` row (`user_id`, `quest_key`, `day_start_ms`, `reward_exp`, `created_at`) and calls `grant_exp` for the reward, in the same transaction.
4. A `UNIQUE (user_id, quest_key, day_start_ms)` constraint on the table is the actual source of truth against double-claiming — a second claim attempt (including a concurrent one) hits an `IntegrityError`, which the endpoint turns into a 409. The earlier read-then-check in step 2 is just a fast path; the constraint is what makes it safe.

Claim state (`claimed: true/false` per quest) is reported by joining `GET .../me` against today's `quest_claims` rows for that user — again nothing about "is this claimed" is cached elsewhere.

## Sequence

```
┌──────────────────────────────┐
│ GET /api/v1/annotate/quests/me│
└───────────────┬───────────────┘
                │
                v
   day_window(now) -> (start_ms, end_ms)
                │
                v
   select_daily_quests(start_ms)  <-- same for every player today
                │
                v
   for each quest: count_progress(metric, start_ms, end_ms)
   + look up whether already claimed today
                │
                v
   respond with progress/completed/claimed per quest


┌────────────────────────────────────────┐
│ POST /api/v1/annotate/quests/{key}/claim │
└───────────────────┬────────────────────┘
                     │
                     v
        key in today's selection? ──no──> 404
                     │yes
                     v
        progress >= target? ──no──> 409
                     │yes
                     v
        insert quest_claims row + grant_exp, commit
                     │
              unique constraint violated? ──yes──> rollback, 409
                     │no
                     v
             200, new exp/expert_level
```

## Configuration reference

Both live in [`backend/src/config.py`](../backend/src/config.py) and can be overridden via environment variables of the same name.

| Constant              | Default          | Meaning                                                        |
|------------------------|------------------|------------------------------------------------------------------|
| `QUEST_TIMEZONE`       | `Europe/Berlin`  | Timezone the daily local-midnight window and day seed are computed in |
| `QUEST_COUNT_PER_DAY`  | `3`              | How many quests are sampled from `CATALOG` each day             |

Individual quest targets and exp rewards are not env-configurable; they're the `QuestTemplate` entries in `CATALOG` (`backend/src/services/quests.py`) and are changed by editing that catalog directly.

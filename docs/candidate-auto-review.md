# Candidate pair auto-review

This page explains how a candidate pair (a proposed image-overlap match) gets automatically decided once enough annotators have voted on it, how experience points (exp) are handed out along the way, and its individual votes move through.

The relevant code lives in [`backend/src/api/v1/annotate/candidates.py`](../backend/src/api/v1/annotate/candidates.py) (function `_recompute_candidate_consensus` and its helpers) and [`backend/src/config.py`](../backend/src/config.py) (the tunable thresholds).

## Step 1: what a candidate pair is

A candidate pair links two images from the same dive that *might* overlap. Before anyone can vote on it, a scientist creates it (status `hidden`) and opens it (status `open`). Once open, annotators submit votes, each a `CandidateAnnotation` row saying either:
- **overlap** (`no_overlap: false`): "yes, these two images show the same scene"
- **no overlap** (`no_overlap: true`): "no, these are different scenes".

Each vote also freezes the voter's `expert_level` at the moment they voted, which matters for Step 2.

## Step 2: two independent ways to reach consensus

Every time a vote is created, corrected, or manually reviewed, the system re-checks whether the candidate pair has reached consensus. There are two independent thresholds. Either one firing is enough to decide the pair. Whichever one is satisfied first wins.

### 2a. Weighted consensus (expert-driven)

Each vote gets a **weight**:

```
weight(vote) = CANDIDATE_CONSENSUS_EXPERT_WEIGHT   if voter.expert_level >= CANDIDATE_CONSENSUS_EXPERT_LEVEL
             = 1                                   otherwise
```

With the defaults (`CANDIDATE_CONSENSUS_EXPERT_LEVEL = 3`, `CANDIDATE_CONSENSUS_EXPERT_WEIGHT = 2`), an expert's vote counts double.

Once the **total weight** of all counted votes reaches `CANDIDATE_CONSENSUS_MIN_WEIGHT` (default `10`), and one side's **share of that weight** reaches `CANDIDATE_CONSENSUS_MIN_SHARE` (default `0.7`), that side wins.

```
overlap_share    = overlap_weight    / total_weight
no_overlap_share = no_overlap_weight / total_weight

total_weight >= CANDIDATE_CONSENSUS_MIN_WEIGHT
    and (overlap_share >= CANDIDATE_CONSENSUS_MIN_SHARE
         or no_overlap_share >= CANDIDATE_CONSENSUS_MIN_SHARE)
```

**Example** — 2 novices (`expert_level = 0`, weight 1) vote "no overlap", then 4 experts (`expert_level = 3`, weight 2) vote "overlap":

```
novice 1: no_overlap   -> weight 1   running: overlap=0   no_overlap=1   total=1
novice 2: no_overlap   -> weight 1   running: overlap=0   no_overlap=2   total=2
expert 1: overlap      -> weight 2   running: overlap=2   no_overlap=2   total=4
expert 2: overlap      -> weight 2   running: overlap=4   no_overlap=2   total=6
expert 3: overlap      -> weight 2   running: overlap=6   no_overlap=2   total=8
expert 4: overlap      -> weight 2   running: overlap=8   no_overlap=2   total=10  <-- MIN_WEIGHT reached

overlap_share = 8 / 10 = 0.8  >= 0.7  -> OVERLAP WINS
```

Note the **raw** vote count here is 6, with only 4 "overlap" votes, a raw share of `4 / 6 ≈ 0.667`, which is *below* 0.7. Expert weighting, not raw majority, is what actually decided this pair. A handful of experts can out-vote a larger group of novices.

### 2b. Raw count / agreement auto-review (cold-start path)

The weighted path needs real expert participation to close quickly. Early on, with few or no experts online, a pair could sit open indefinitely even with a clear, unanimous novice majority. The **raw** threshold exists specifically for that case. It ignores expert weighting entirely and looks only at plain vote counts:

```
overlap_count    = number of counted votes for "overlap"
no_overlap_count = number of counted votes for "no overlap"
total_count      = overlap_count + no_overlap_count

overlap_share    = overlap_count    / total_count
no_overlap_share = no_overlap_count / total_count

total_count >= CANDIDATE_MIN_ANNOTATIONS
    and (overlap_share >= CANDIDATE_AGREEMENT_THRESHOLD
         or no_overlap_share >= CANDIDATE_AGREEMENT_THRESHOLD)
```

With the defaults (`CANDIDATE_MIN_ANNOTATIONS = 5`, CANDIDATE_AGREEMENT_THRESHOLD = 0.7`), 5 votes with at least 70% agreeing is enough, no experts required.

**Example** (5 novices vote, 4 "overlap" and 1 "no overlap")

```
vote 1: overlap       total=1   overlap_share=1/1=1.00
vote 2: overlap       total=2   overlap_share=2/2=1.00
vote 3: overlap       total=3   overlap_share=3/3=1.00
vote 4: no_overlap    total=4   overlap_share=3/4=0.75
vote 5: overlap       total=5   overlap_share=4/5=0.80  <-- MIN_ANNOTATIONS reached, share >= 0.7

OVERLAP WINS
```

### 2c. Which check runs first

Both checks run on every recompute; the weighted check is evaluated first, then the raw check, and the first one to produce a winner is used. In practice, because a single vote's weight is capped at `CANDIDATE_CONSENSUS_EXPERT_WEIGHT` (2), the weighted threshold can never be reached with fewer than `CANDIDATE_MIN_ANNOTATIONS` raw votes either. So the raw check is nearly always what actually resolves a pair, and the weighted check only "wins" in mixed-expert scenarios like the Step 2a example above, where raw agreement alone would not have been enough.

```
                        ┌─────────────────────────┐
                        │ a vote is created,      │
                        │ corrected, or reviewed  │
                        └────────────┬────────────┘
                                     │
                                     v
                     ┌───────────────────────────────┐
                     │ candidate pair still "open"?  │
                     └───────────────┬───────────────┘
                              no ────┤──── yes
                                     │
                                     v
                     ┌───────────────────────────────┐
                     │ weighted consensus threshold  │
                     │ met? (2a)                     │
                     └───────────────┬───────────────┘
                              no ────┤──── yes ──────────┐
                                     │                   │
                                     v                   │
                     ┌───────────────────────────────┐   │
                     │ raw count/agreement threshold │   │
                     │ met? (2b)                     │   │
                     └───────────────┬───────────────┘   │
                              no ────┤──── yes ──────────┤
                                     │                   │
                                     v                   v
                     ┌───────────────────────┐  ┌────────────────────┐
                     │ nothing happens yet;  │  │ AUTO-REVIEW FIRES  │
                     │ pair stays "open"     │  │ (see Step 3)       │
                     └───────────────────────┘  └────────────────────┘
```

## Step 3: what happens when auto-review fires

The moment either threshold is met, the system performs one atomic "auto-review" — all of the following happen together, in the same transaction, as soon as consensus is reached (never speculatively before that point):

1. **Every counted vote is closed out.** A vote that agrees with the winning side becomes `approved`; a vote on the losing side becomes `review_failed`. Both get `reviewed_at` stamped. `reviewed_by` stays `NULL` on both the votes and the candidate pair, because there is no human reviewer in this path. It is the system, not a person, closing the case.
2. **Exp is granted to the winning side only.** Every annotator whose vote agreed with the winning side receives `CANDIDATE_ANNOTATION_REVIEW_EXP` exp (the same amount a human reviewer's approval would grant). Voters on the losing side get nothing. No one gets a "reviewer" bonus, because there is no reviewer.
3. **The candidate pair itself closes**, its status set to `has_overlap` or `no_overlap` to match the winning side.
4. **If the winning side is "overlap"**, a corresponding `ImagePair` is created automatically (status `hidden`), so the pair becomes available for the next stage (point-by-point annotation) without a scientist needing to intervene. If an `ImagePair` for that image combination already exists, nothing new is created.

**Continuing the raw-count example from 2b** (4 overlap votes win, 1 no overlap vote loses):

| Voter   | Vote        | Result           | Exp granted?                           |
|---------|-------------|------------------|----------------------------------------|
| voter 1 | overlap     | `approved`       | Yes, `CANDIDATE_ANNOTATION_REVIEW_EXP` |
| voter 2 | overlap     | `approved`       | Yes, `CANDIDATE_ANNOTATION_REVIEW_EXP` |
| voter 3 | overlap     | `approved`       | Yes, `CANDIDATE_ANNOTATION_REVIEW_EXP` |
| voter 4 | no overlap  | `review_failed`  | No                                     |
| voter 5 | overlap     | `approved`       | Yes, `CANDIDATE_ANNOTATION_REVIEW_EXP` |

Candidate pair: `open` -> `has_overlap`, and a new hidden `ImagePair` is created for the same two images.

## Step 4: this is separate from manual human review

Auto-review is not the only way a vote gets closed out. A human reviewer (with a sufficiently high `expert_level`, or the scientist/admin role) can also manually approve or fail an individual pending vote, at any time, before consensus is reached. This is the `review/{annotation_uuid}/approve` and `review/{annotation_uuid}/fail` endpoints. 

That path:
- Grants `CANDIDATE_ANNOTATION_REVIEW_EXP` to the **reviewer**, always.
- Grants `CANDIDATE_ANNOTATION_REVIEW_EXP` to the vote's **creator** too, but only if the reviewer approved it.
- Sets `reviewed_by` to the reviewer's own id (not `NULL`), since here there genuinely is a human reviewer.
- Then re-runs the exact same consensus check described in Step 2. A manual review can itself be the vote that tips a pair into auto-review.

One edge case worth calling out: if a vote was already manually approved before auto-review fires, and it turns out to be on the losing side, it still flips to `review_failed` (no exp is clawed back from the earlier manual approval). If it's on the winning side, its creator receives a *second* `CANDIDATE_ANNOTATION_REVIEW_EXP` grant,once for the manual approval, once for auto-review. This is accepted as-is: every counted vote is always reprocessed uniformly when consensus fires, regardless of whether a human already looked at it individually.

## State machines

### Candidate pair status

```
   hidden ──(scientist opens it)──> open
                                      │
                                      │ auto-review fires (Step 3),
                                      │ or a scientist manually sets status
                                      │
                        ┌─────────────┼─────────────┐
                        v             v             v
                  has_overlap    no_overlap      deleted
                        │
                        │ (creates a hidden ImagePair,
                        │  if one doesn't exist yet)
                        v
                (ready for point annotation)
```

- `hidden` -> `open`: a scientist explicitly opens a pair for voting.
- `open` -> `has_overlap` / `no_overlap`: automatic, via auto-review (Step 3), or manual via the scientist-only batch status-change endpoint.
- Any status -> `deleted`: manual, scientist-only.
- Once a pair leaves `open`, no further votes are accepted (`409 Candidate not open`), and auto-review never re-fires — the guard at the top of `_recompute_candidate_consensus` short-circuits immediately if the pair isn't `open`.

### Individual vote (`CandidateAnnotation`) status

```
                    ┌──────────────────┐
     vote cast ───> │  review_pending  │
                    └─────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        v                     v                     v
   auto-review:          manual review:     creator corrects their
   agrees with           approve / fail     own vote within the time
   winning side              │              limit, before it's
        │                    │              reviewed (stays review_pending,
        v                    v              no_overlap value changes)
   ┌──────────┐       ┌─────────────┐
   │ approved │       │  approved / │            
   └──────────┘       │review_failed│               
        │             └─────────────┘               
        │
   auto-review:
   disagrees with
   winning side
        │
        v
  ┌───────────────┐
  │ review_failed │
  └───────────────┘
```

- `review_pending` is the only status a vote can be corrected from (and only by its own creator, within `SELF_CORRECTION_TIME_LIMIT_MS` of creating it).
- `approved` and `review_failed` are both terminal for that vote (either from a human reviewer or auto-review) and are the only two statuses counted as active votes toward future consensus recomputations (`review_pending` and `approved` are counted, `review_failed` is not).

## Configuration reference

All of these live in [`backend/src/config.py`](../backend/src/config.py) and can be overridden via environment variables of the same name.

| Constant                             | Default | Meaning                                                                  |
|--------------------------------------|---------|--------------------------------------------------------------------------|
| `CANDIDATE_CONSENSUS_MIN_WEIGHT`     | `10`    | Minimum total weighted votes before weighted consensus (2a) can fire     |
| `CANDIDATE_CONSENSUS_MIN_SHARE`      | `0.7`   | Minimum weighted vote share one side needs to win (2a)                   |
| `CANDIDATE_CONSENSUS_EXPERT_LEVEL`   | `3`     | `expert_level` at/above which a vote counts as "expert" (2a)             |
| `CANDIDATE_CONSENSUS_EXPERT_WEIGHT`  | `2`     | Weight an expert vote counts as, instead of `1` (2a)                     |
| `CANDIDATE_MIN_ANNOTATIONS`          | `5`     | Minimum raw vote count before raw auto-review (2b) can fire              |
| `CANDIDATE_AGREEMENT_THRESHOLD`      | `0.7`   | Minimum raw vote share one side needs to win (2b)                        |
| `CANDIDATE_ANNOTATION_REVIEW_EXP`    | `5`     | Exp granted per winning/approved vote (via auto-review or manual review) |

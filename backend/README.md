# Backend

## Project Structure
```
backend/
├── src/
│   ├── api/              # fastapi
│   │   ├── v1/
│   │   │   ├── admin/    # for administrative stuff
│   │   │   ├── annotate/ # annotation for normal users
│   │   │   ├── auth/     # open routes for authentication (cookie with user uuid)
│   │   │   ├── dataset/  # import/export of datasets
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── middleware/   # for access management
│   │   ├── __init__.py
│   │   └── router.py
│   ├── migrations/
│   │   └── 0001_initial_schema.sql
│   ├── models/           # pydantic models
│   ├── schema/           # sqlalchemy models
│   ├── config.py         # env-var config + uuid<->cookie encoding
│   ├── constants.py       # Role enum + role hierarchy
│   ├── db.py             # SQLAlchemy engine/session setup
│   ├── bootstrap_admin.py # one-off script to create the first admin user
│   └── main.py           # Entrypoint
├── assets/               # public static image directory, served at /assets
└── tests/                # pytest tests
```

## Running

From the `backend/` directory:

```sh
# start the API (applies pending migrations on startup)
devenv shell -- uvicorn src.main:app --reload

# or
devenv shell -- python -m src.main
```

From the repo root:

```sh
devenv shell -- bash -c "cd backend && python -m pytest"
```

## Auth model

There is no password. Authentication is a single self-service signup: `POST /api/v1/auth/signup {"username": "..."}` creates a new `annotator`-role user and sets a `session_uuid` cookie holding that user's raw uuid (hex encoded) - the cookie value *is* the credential, there is no login endpoint. This is an accepted tradeoff for a low-stakes prototype.

Roles are hierarchical: `admin` > `scientist` > `annotator`, stored in `users.role`. `expert_level` is a separate, unrelated field (an annotation weight, not a permission level). A single middleware (`src/api/middleware/auth_middleware.py`) enforces, by URL prefix:

- `/api/v1/auth/*` - public
- `/api/v1/annotate/*` - any authenticated role
- `/api/v1/dataset/*` - scientist or admin
- `/api/v1/admin/*` - admin only
- `/assets/*` and everything outside `/api` - public

## Bootstrapping the first admin

Self-signup always forces `role='annotator'`, so the very first admin must be created directly:

```sh
cd backend && devenv shell -- python -m src.bootstrap_admin --username admin
```

This prints the new admin's uuid. Save it - it is the only credential and there is no recovery if lost. Set it manually as the `session_uuid` cookie (e.g. via browser devtools, or `curl -b "session_uuid=<hex>"`) to authenticate as this admin.

## Config (env vars)

| Variable               | Default             | Purpose                                      |
| ---------------------- | ------------------- | -------------------------------------------- |
| DATABASE_PATH          | backend/data/app.db | SQLite file location                         |
| ASSETS_DIR             | backend/assets      | Public static image directory                |
| COOKIE_NAME            | session_uuid        | Auth cookie name                             |
| COOKIE_SECURE          | false               | Set `true` behind TLS in any real deployment |
| COOKIE_MAX_AGE_SECONDS | 31536000 (1 year)   | Cookie lifetime                              |

## Migrations

Schema changes are hand-written `.sql` files in `src/migrations/`, numbered sequentially (`0001_...`, `0002_...`). They are applied automatically on startup by `src/migrations/runner.py`, which tracks what's been applied in a `schema_migrations` bookkeeping table. Migration files must not contain their own `BEGIN`/`COMMIT`/`PRAGMA foreign_keys` statements - the runner supplies the transaction wrapper. SQLAlchemy models under `src/schema/` mirror the SQL schema for querying and must be updated by hand alongside any new migration (they are not used to generate migrations).

`image_statuses`, `pair_statuses`, `candidate_statuses`, and `annotation_statuses` are fixed lookup tables. Their rows are seeded once via `INSERT OR IGNORE` in the migration and never modified at runtime. There is intentionally no admin/CRUD endpoint for them. The Python-side source of truth for valid status values is the corresponding `StrEnum` + int-mapping dict pair in `src/constants.py`, not the DB rows. The DB rows exist only for FK referential integrity and so the `description` column can document them for anyone browsing the database directly. Adding a new status value is a schema change. A new migration inserting the row and a matching enum member/dict entries in `constants.py`, in the same change. `tests/test_status_enum_sync.py` guards against the two drifting apart.

# Adding a new dataset controller

Playbook for adding a new CRUD resource ("controller") to the `dataset` domain, following
the exact conventions already used by `src/api/v1/dataset/{regions,cameras,dives}.py`. Use
this as a checklist when a new titled entity (e.g. `sites`, `vessels`, `expeditions`) needs
create/update/list endpoints.

Every step below uses `<name>` (snake_case singular, e.g. `site`), `<Name>` (PascalCase,
e.g. `Site`), and `<table>` (snake_case plural, e.g. `sites`) — substitute your resource.
If the resource has foreign keys to other dataset entities, add those columns/fields
alongside the standard ones; the `dives` resource (FKs to `regions` and `cameras`) is the
reference example for that case.

## 1. Migration — `src/migrations/000N_<table>.sql`

Next sequential number after the highest existing file in `src/migrations/`. Migration
files must NOT contain their own `BEGIN`/`COMMIT`/`PRAGMA foreign_keys` — the runner
(`src/migrations/runner.py`) supplies the transaction wrapper and applies pending files
automatically on app startup, tracking them in a `schema_migrations` table.

```sql
CREATE TABLE IF NOT EXISTS <table> (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid        BLOB    NOT NULL UNIQUE CHECK(LENGTH(uuid) = 16),
    created_at  INTEGER NOT NULL, -- unix millis
    created_by  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title       TEXT    NOT NULL UNIQUE CHECK(LENGTH(title) < 128),
    metadata    TEXT, -- json
    description TEXT    CHECK(description IS NULL OR LENGTH(description) < 1024)
    -- plus any FK columns, e.g.:
    -- region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE RESTRICT
);
```

## 2. SQLAlchemy schema — `src/schema/<table>.py`

Mirrors the migration by hand — it is not generated from the SQL, so keep the two in sync
yourself.

```python
from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class <Name>(Base):
    __tablename__ = "<table>"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # plus any FK id columns
```

## 3. Pydantic models — add to `src/models/dataset.py`

All dataset-domain request/response models live in this one file (not one file per
resource) — add yours alongside `DiveCreateRequest`/`DiveResponse` etc.

- `<Name>CreateRequest`: `uuid: UUID`, `title: str = Field(min_length=1, max_length=127)`,
  `metadata: dict[str, Any] | None = None`, `description: str | None = Field(default=None, max_length=1023)`,
  plus any FK fields typed as `UUID`.
- `<Name>UpdateRequest`: same fields, but every one is `Optional` with **no default other
  than `None`**. This matters: `apply_partial_update` (see step 4) distinguishes "field
  omitted" from "field explicitly set to null" via Pydantic's `model_fields_set`, which only
  works if every field is declared this way.
- `<Name>Response`: `uuid`, `created_at: int`, `created_by: UUID`, `title: str`,
  `metadata: Any | None`, `description: str | None`, plus FK fields as `UUID`.
- `<Name>ListResponse` (only if you're adding a list endpoint, step 5): one field, named
  after the plural resource (e.g. `dives: list[DiveResponse]`), holding `list[<Name>Response]`.

## 4. Router — `src/api/v1/dataset/<table>.py`

```python
router = APIRouter()
```

- `_to_response(<name>, db) -> <Name>Response`: resolves `created_by` (and any FK ids) to
  their UUIDs via `db.get(Model, <name>.fk_id)`, decodes metadata via `decode_metadata`
  from `src.api.v1.dataset._metadata`.
- `_resolve_<fk>_id(db, uuid) -> int` per foreign key: uses `get_by_uuid` from
  `src.services.lookups`, raises `HTTPException(404, "<Fk> not found")` if missing.
- `POST /create` (`status_code=201`): call `require_current_user(request)` (from
  `src.api.deps`) to get the acting user; build the ORM row with `uuid=payload.uuid.bytes`,
  `created_at=now_ms()` (from `src.util`), `created_by=user.id`,
  `metadata_json=encode_metadata(payload.metadata)`; `db.add` + `db.commit`; catch
  `IntegrityError` → `db.rollback()` + `HTTPException(409, "<Name> already exists")`;
  `db.refresh`; return `_to_response`.
- `POST /update`: look up by uuid via `get_by_uuid`, 404 if missing. Compute the columns to
  change with `apply_partial_update(payload, nullable_columns={"metadata_json", "description"}, field_map={...})`;
  re-encode metadata if present in the result; apply FK updates separately by checking
  `"<fk>" in payload.model_fields_set and payload.<fk> is not None`. Same commit /
  `IntegrityError` → 409 handling as create. Return `_to_response`.

## 5. List endpoint (optional) — same file, `src/api/v1/dataset/<table>.py`

If a "list all `<table>`" endpoint is needed, add it to `<table>.py` next to
create/update, registered at `""` (which combines with the `prefix="/<table>"` from step 6
to give `GET /api/v1/dataset/<table>`, no trailing slash — see `list_dives` in
`dives.py` for the reference example). Do a single joined query across the resource and
any FK tables rather than looping `_to_response` per row, to avoid one query per row:

```python
@router.get("", response_model=<Name>ListResponse)
def list_<table>(db: Session = Depends(get_db)):
    rows = db.execute(
        select(<Name> /* , <FkModel>, ... */)
        # .join(<FkModel>, <Name>.fk_id == <FkModel>.id)
        .order_by(<Name>.created_at)
    ).all()
    return <Name>ListResponse(<table>=[... _to_response-equivalent construction ...])
```

## 6. Wire it up — `src/api/v1/dataset/router.py`

```python
from src.api.v1.dataset.<table> import router as <table>_router
...
router.include_router(<table>_router, prefix="/<table>")
```

No manual role-gating code is needed in the router itself: `AuthMiddleware`
(`src/api/middleware/auth_middleware.py`) already enforces `scientist`-or-above for every
path under `/api/v1/dataset/*`.

## 7. Tests — `backend/tests/test_dataset_<table>.py`

Follow `tests/test_dataset_dives.py` structure exactly:

- A `scientist` fixture that seeds and logs in a scientist user via the `seed_user` /
  `login_as` fixtures from `tests/conftest.py`, and a local `_new_uuid()` helper.
- `test_create_<name>_happy_path` — asserts every response field, including that
  `created_by` matches the logged-in user's uuid and `created_at` is an `int`.
- `test_create_<name>_defaults_are_null` — creating with only required fields leaves
  `metadata`/`description` (and any optional FK) null.
- One 404 test per foreign key — creating with an unknown FK reference.
- `test_create_<name>_malformed_uuid_is_422`.
- `test_create_<name>_unique_title_conflicts` — duplicate title is a 409.
- `test_update_title_missing_is_noop` — a field omitted from the update payload doesn't change.
- `test_update_explicit_null_clears_nullable` — explicit `null` clears `metadata`/`description`.
- `test_update_explicit_null_title_is_noop` — explicit `null` on a non-nullable column
  (like `title`) is a no-op, not a clear or an error.
- `test_update_<fk>_to_different_existing` and `test_update_<fk>_to_unknown_is_404` per FK.
- `test_update_unknown_<name>_is_404`.
- `test_<table>_role_gating_annotator_forbidden` — an `annotator`-role user gets `403`.

Only touch `constants.py` / `tests/test_status_enum_sync.py` if the new resource introduces
a fixed status enum + lookup table (like `image_statuses`) — plain titled entities
(regions, cameras, dives) don't need this.

## 8. Verify

From `backend/`:

```sh
devenv shell -- python -m pytest tests/test_dataset_<table>.py
```

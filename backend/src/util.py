import time


def now_ms() -> int:
    """Current unix time in milliseconds."""
    return int(time.time() * 1000)


def apply_partial_update(
    payload,
    *,
    nullable_columns: set[str],
    field_map: dict[str, str],
) -> dict[str, object]:
    """Compute the columns to write for a partial (PATCH-style) update.

    Implements the missing/null/value truth table:

    | json key present? | value  | required-type column | nullable-type column |
    |-------------------|--------|----------------------|----------------------|
    | missing           | -      | no update            | no update            |
    | present           | null   | no update            | set NULL             |
    | present           | value  | update               | update               |

    "present" is detected via Pydantic v2 `payload.model_fields_set`, which
    distinguishes an explicitly-supplied `null` from an omitted key (so update
    request models must declare every field `Optional` with no default).

    `field_map` maps request-model field name -> ORM column/attribute name.
    `nullable_columns` is the set of mapped column names that are nullable-type.
    Returns `{column_name: value}` for the columns that should actually change.
    """
    result: dict[str, object] = {}
    for field, column in field_map.items():
        if field not in payload.model_fields_set:
            continue
        value = getattr(payload, field)
        if value is None:
            if column in nullable_columns:
                result[column] = None
            # else: null on a required column -> no update
            continue
        result[column] = value
    return result

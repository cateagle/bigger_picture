from typing import Optional

from pydantic import BaseModel

from src.util import apply_partial_update


class _UpdateModel(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


def _payload(**kwargs) -> _UpdateModel:
    # Only keys passed here land in `model_fields_set`.
    return _UpdateModel(**kwargs)


FIELD_MAP = {"title": "title", "description": "description"}
NULLABLE = {"description"}


def test_missing_field_absent_from_result():
    result = apply_partial_update(_payload(), nullable_columns=NULLABLE, field_map=FIELD_MAP)
    assert result == {}


def test_explicit_null_on_nullable_is_present_as_none():
    result = apply_partial_update(
        _payload(description=None), nullable_columns=NULLABLE, field_map=FIELD_MAP
    )
    assert result == {"description": None}


def test_explicit_null_on_required_is_absent():
    result = apply_partial_update(
        _payload(title=None), nullable_columns=NULLABLE, field_map=FIELD_MAP
    )
    assert result == {}


def test_present_value_is_included():
    result = apply_partial_update(
        _payload(title="hello", description="world"),
        nullable_columns=NULLABLE,
        field_map=FIELD_MAP,
    )
    assert result == {"title": "hello", "description": "world"}


def test_field_map_renames_to_column():
    payload = _payload(title="t")
    result = apply_partial_update(
        payload, nullable_columns=set(), field_map={"title": "renamed_column"}
    )
    assert result == {"renamed_column": "t"}

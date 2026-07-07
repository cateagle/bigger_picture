"""Shared metadata JSON encode/decode helpers for dataset routers.

The `metadata` field is exposed to clients as an arbitrary JSON object but is
stored in a TEXT column (`metadata_json` ORM attribute). These helpers keep the
serialization consistent between the regions and cameras routers.
"""

import json
from typing import Any


def encode_metadata(value: Any | None) -> str | None:
    """Serialize a metadata object into JSON text (None stays None/NULL)."""
    if value is None:
        return None
    return json.dumps(value)


def decode_metadata(stored: str | None) -> Any | None:
    """Deserialize stored JSON text back into an object (None stays None)."""
    if stored is None:
        return None
    return json.loads(stored)

import uuid

import pytest


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_create_region_happy_path_with_metadata(client, scientist):
    u = _new_uuid()
    meta = {"depth": 12, "notes": ["a", "b"]}
    resp = client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": u, "title": "north reef", "metadata": meta, "description": "d"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["uuid"] == u
    assert body["title"] == "north reef"
    assert body["metadata"] == meta
    assert body["description"] == "d"
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))


def test_create_region_defaults(client, scientist):
    resp = client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": _new_uuid(), "title": "south reef"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["metadata"] is None
    assert body["description"] is None


def test_metadata_round_trips_as_json(client, scientist):
    u = _new_uuid()
    meta = {"nested": {"x": 1}, "list": [1, 2, 3], "flag": True}
    client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": u, "title": "east reef", "metadata": meta},
    )
    # fetch via update no-op to read back
    resp = client.post("/api/v1/dataset/regions/update", json={"uuid": u})
    assert resp.status_code == 200
    assert resp.json()["metadata"] == meta


def test_create_region_unique_title_conflicts(client, scientist):
    client.post("/api/v1/dataset/regions/create", json={"uuid": _new_uuid(), "title": "dup"})
    resp = client.post("/api/v1/dataset/regions/create", json={"uuid": _new_uuid(), "title": "dup"})
    assert resp.status_code == 409


def test_update_metadata_value(client, scientist):
    u = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": u, "title": "r1"})
    resp = client.post(
        "/api/v1/dataset/regions/update",
        json={"uuid": u, "metadata": {"new": 1}},
    )
    assert resp.status_code == 200
    assert resp.json()["metadata"] == {"new": 1}


def test_update_explicit_null_clears_metadata_and_description(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": u, "title": "r2", "metadata": {"a": 1}, "description": "keep"},
    )
    resp = client.post(
        "/api/v1/dataset/regions/update",
        json={"uuid": u, "metadata": None, "description": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["metadata"] is None
    assert body["description"] is None


def test_update_missing_is_noop(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": u, "title": "r3", "metadata": {"a": 1}, "description": "keep"},
    )
    resp = client.post("/api/v1/dataset/regions/update", json={"uuid": u, "title": "r3b"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "r3b"
    assert body["metadata"] == {"a": 1}
    assert body["description"] == "keep"


def test_update_explicit_null_on_title_is_noop(client, scientist):
    u = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": u, "title": "r4"})
    resp = client.post("/api/v1/dataset/regions/update", json={"uuid": u, "title": None})
    assert resp.status_code == 200
    assert resp.json()["title"] == "r4"


def test_update_unknown_uuid_is_404(client, scientist):
    resp = client.post("/api/v1/dataset/regions/update", json={"uuid": _new_uuid(), "title": "x"})
    assert resp.status_code == 404


def test_regions_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post("/api/v1/dataset/regions/create", json={"uuid": _new_uuid(), "title": "t"})
    assert resp.status_code == 403

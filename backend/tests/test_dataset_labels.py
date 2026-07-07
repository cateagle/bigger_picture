import uuid

import pytest


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_create_label_happy_path(client, scientist):
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": u, "scope": "species", "title": "fish", "description": "a fish"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["uuid"] == u
    assert body["scope"] == "species"
    assert body["title"] == "fish"
    assert body["description"] == "a fish"
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))
    assert isinstance(body["created_at"], int)


def test_create_label_default_description_is_null(client, scientist):
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": _new_uuid(), "scope": "species", "title": "coral"},
    )
    assert resp.status_code == 201
    assert resp.json()["description"] is None


def test_create_label_malformed_uuid_is_422(client, scientist):
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": "not-a-uuid", "scope": "s", "title": "t"},
    )
    assert resp.status_code == 422


def test_create_label_unique_scope_title_conflicts(client, scientist):
    client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": _new_uuid(), "scope": "species", "title": "eel"},
    )
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": _new_uuid(), "scope": "species", "title": "eel"},
    )
    assert resp.status_code == 409


def test_update_missing_is_noop(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": u, "scope": "species", "title": "ray", "description": "keep"},
    )
    resp = client.post("/api/v1/dataset/labels/update", json={"uuid": u, "title": "manta ray"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "manta ray"
    assert body["scope"] == "species"
    assert body["description"] == "keep"


def test_update_explicit_null_clears_description(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": u, "scope": "species", "title": "shark", "description": "keep"},
    )
    resp = client.post("/api/v1/dataset/labels/update", json={"uuid": u, "description": None})
    assert resp.status_code == 200
    assert resp.json()["description"] is None


def test_update_explicit_null_on_required_is_noop(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": u, "scope": "species", "title": "tuna"},
    )
    resp = client.post("/api/v1/dataset/labels/update", json={"uuid": u, "title": None})
    assert resp.status_code == 200
    assert resp.json()["title"] == "tuna"


def test_update_unknown_uuid_is_404(client, scientist):
    resp = client.post("/api/v1/dataset/labels/update", json={"uuid": _new_uuid(), "title": "x"})
    assert resp.status_code == 404


def test_labels_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": _new_uuid(), "scope": "s", "title": "t"},
    )
    assert resp.status_code == 403


def test_labels_admin_allowed(client, seed_user, login_as):
    login_as(seed_user(username="root", role="admin"))
    resp = client.post(
        "/api/v1/dataset/labels/create",
        json={"uuid": _new_uuid(), "scope": "s", "title": "t"},
    )
    assert resp.status_code == 201

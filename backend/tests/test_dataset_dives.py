import uuid

import pytest


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _make_region(client, title="reg") -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/regions/create",
        json={"uuid": u, "title": title},
    )
    assert resp.status_code == 201, resp.text
    return u


def _make_camera(client, title="cam") -> str:
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/cameras/create",
        json={"uuid": u, "title": title},
    )
    assert resp.status_code == 201, resp.text
    return u


def test_create_dive_happy_path(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={
            "uuid": u,
            "title": "dive 1",
            "metadata": {"depth": 12},
            "description": "first dive",
            "region": region,
            "camera": camera,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uuid"] == u
    assert body["title"] == "dive 1"
    assert body["metadata"] == {"depth": 12}
    assert body["description"] == "first dive"
    assert body["region"] == region
    assert body["camera"] == camera
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))
    assert isinstance(body["created_at"], int)


def test_create_dive_defaults_are_null(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": _new_uuid(), "title": "dive plain", "region": region, "camera": camera},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["metadata"] is None
    assert body["description"] is None


def test_create_dive_unknown_region_is_404(client, scientist):
    camera = _make_camera(client)
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": _new_uuid(), "title": "d", "region": _new_uuid(), "camera": camera},
    )
    assert resp.status_code == 404
    assert "Region" in resp.json()["detail"]


def test_create_dive_unknown_camera_is_404(client, scientist):
    region = _make_region(client)
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": _new_uuid(), "title": "d", "region": region, "camera": _new_uuid()},
    )
    assert resp.status_code == 404
    assert "Camera" in resp.json()["detail"]


def test_create_dive_malformed_uuid_is_422(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": "not-a-uuid", "title": "d", "region": region, "camera": camera},
    )
    assert resp.status_code == 422


def test_create_dive_unique_title_conflicts(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": _new_uuid(), "title": "dupe", "region": region, "camera": camera},
    )
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": _new_uuid(), "title": "dupe", "region": region, "camera": camera},
    )
    assert resp.status_code == 409


def test_update_title_missing_is_noop(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={
            "uuid": u,
            "title": "orig",
            "description": "keep",
            "region": region,
            "camera": camera,
        },
    )
    resp = client.post("/api/v1/dataset/dives/update", json={"uuid": u, "title": "renamed"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "renamed"
    assert body["description"] == "keep"
    assert body["region"] == region
    assert body["camera"] == camera


def test_update_explicit_null_clears_nullable(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={
            "uuid": u,
            "title": "d",
            "metadata": {"a": 1},
            "description": "keep",
            "region": region,
            "camera": camera,
        },
    )
    resp = client.post(
        "/api/v1/dataset/dives/update",
        json={"uuid": u, "metadata": None, "description": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["metadata"] is None
    assert body["description"] is None


def test_update_explicit_null_title_is_noop(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": "keeptitle", "region": region, "camera": camera},
    )
    resp = client.post("/api/v1/dataset/dives/update", json={"uuid": u, "title": None})
    assert resp.status_code == 200
    assert resp.json()["title"] == "keeptitle"


def test_update_metadata_value(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": "d", "region": region, "camera": camera},
    )
    resp = client.post(
        "/api/v1/dataset/dives/update",
        json={"uuid": u, "metadata": {"new": True}},
    )
    assert resp.status_code == 200
    assert resp.json()["metadata"] == {"new": True}


def test_update_region_and_camera_to_different_existing(client, scientist):
    region = _make_region(client, title="r1")
    camera = _make_camera(client, title="c1")
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": "d", "region": region, "camera": camera},
    )
    region2 = _make_region(client, title="r2")
    camera2 = _make_camera(client, title="c2")
    resp = client.post(
        "/api/v1/dataset/dives/update",
        json={"uuid": u, "region": region2, "camera": camera2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["region"] == region2
    assert body["camera"] == camera2


def test_update_explicit_null_region_is_noop(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": "d", "region": region, "camera": camera},
    )
    resp = client.post("/api/v1/dataset/dives/update", json={"uuid": u, "region": None})
    assert resp.status_code == 200
    assert resp.json()["region"] == region


def test_update_region_to_unknown_is_404(client, scientist):
    region = _make_region(client)
    camera = _make_camera(client)
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/dives/create",
        json={"uuid": u, "title": "d", "region": region, "camera": camera},
    )
    resp = client.post(
        "/api/v1/dataset/dives/update",
        json={"uuid": u, "region": _new_uuid()},
    )
    assert resp.status_code == 404


def test_update_unknown_dive_is_404(client, scientist):
    resp = client.post("/api/v1/dataset/dives/update", json={"uuid": _new_uuid(), "title": "x"})
    assert resp.status_code == 404


def test_dives_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post(
        "/api/v1/dataset/dives/create",
        json={
            "uuid": _new_uuid(),
            "title": "t",
            "region": _new_uuid(),
            "camera": _new_uuid(),
        },
    )
    assert resp.status_code == 403

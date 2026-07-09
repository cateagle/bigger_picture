import uuid

from src.schema.users import User


def _admin(seed_user, login_as):
    admin = seed_user(username="admin", role="admin")
    login_as(admin)
    return admin


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_admin_creates_user_defaults(client, seed_user, login_as):
    admin = _admin(seed_user, login_as)
    u = _new_uuid()
    resp = client.post("/api/v1/admin/users/create", json={"uuid": u, "username": "newbie"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "newbie"
    assert body["role"] == "annotator"
    assert body["expert_level"] == 0

    factory = client.app.state.session_factory
    with factory() as session:
        row = session.query(User).filter(User.username == "newbie").one()
        assert row.created_by == admin.id
        assert row.uuid == uuid.UUID(u).bytes
        assert row.created_at > 0


def test_admin_creates_user_with_role_ignores_expert_level(client, seed_user, login_as):
    _admin(seed_user, login_as)
    resp = client.post(
        "/api/v1/admin/users/create",
        json={"uuid": _new_uuid(), "username": "sci", "role": "scientist", "expert_level": 3},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "scientist"
    assert body["expert_level"] == 0
    assert body["exp"] == 0


def test_create_duplicate_username_conflicts(client, seed_user, login_as):
    _admin(seed_user, login_as)
    client.post("/api/v1/admin/users/create", json={"uuid": _new_uuid(), "username": "dup"})
    resp = client.post("/api/v1/admin/users/create", json={"uuid": _new_uuid(), "username": "dup"})
    assert resp.status_code == 409


def test_create_malformed_uuid_is_422(client, seed_user, login_as):
    _admin(seed_user, login_as)
    resp = client.post("/api/v1/admin/users/create", json={"uuid": "not-a-uuid", "username": "bad"})
    assert resp.status_code == 422


def test_create_invalid_role_is_422(client, seed_user, login_as):
    _admin(seed_user, login_as)
    resp = client.post(
        "/api/v1/admin/users/create",
        json={"uuid": _new_uuid(), "username": "x", "role": "wizard"},
    )
    assert resp.status_code == 422


def test_update_changes_username(client, seed_user, login_as):
    _admin(seed_user, login_as)
    u = _new_uuid()
    client.post("/api/v1/admin/users/create", json={"uuid": u, "username": "before"})
    resp = client.post("/api/v1/admin/users/update", json={"uuid": u, "username": "after"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "after"


def test_update_explicit_null_is_noop(client, seed_user, login_as):
    _admin(seed_user, login_as)
    u = _new_uuid()
    client.post(
        "/api/v1/admin/users/create",
        json={"uuid": u, "username": "keep", "role": "scientist", "expert_level": 2},
    )
    resp = client.post(
        "/api/v1/admin/users/update",
        json={"uuid": u, "username": None, "role": None, "expert_level": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "keep"
    assert body["role"] == "scientist"
    assert body["expert_level"] == 0


def test_update_sets_role_but_ignores_expert_level(client, seed_user, login_as):
    _admin(seed_user, login_as)
    u = _new_uuid()
    client.post("/api/v1/admin/users/create", json={"uuid": u, "username": "promote"})
    resp = client.post(
        "/api/v1/admin/users/update",
        json={"uuid": u, "role": "scientist", "expert_level": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "scientist"
    assert body["expert_level"] == 0


def test_update_unknown_uuid_is_404(client, seed_user, login_as):
    _admin(seed_user, login_as)
    resp = client.post("/api/v1/admin/users/update", json={"uuid": _new_uuid(), "username": "ghost"})
    assert resp.status_code == 404


def test_non_admin_is_403(client, seed_user, login_as):
    scientist = seed_user(username="sci", role="scientist")
    login_as(scientist)
    resp = client.post("/api/v1/admin/users/create", json={"uuid": _new_uuid(), "username": "x"})
    assert resp.status_code == 403


def test_unauthenticated_is_401(client):
    resp = client.post("/api/v1/admin/users/create", json={"uuid": _new_uuid(), "username": "x"})
    assert resp.status_code == 401

import uuid

import pytest


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_create_fun_fact_happy_path(client, scientist):
    u = _new_uuid()
    fact = {"text": "Octopuses have three hearts."}
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "octopus hearts", "fact": fact, "min_level": 2},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["uuid"] == u
    assert body["title"] == "octopus hearts"
    assert body["fact"] == fact
    assert body["min_level"] == 2
    assert body["region"] is None
    assert body["created_by"] == str(uuid.UUID(bytes=scientist.uuid))


def test_create_fun_fact_defaults(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "default fact", "fact": {"text": "hi"}},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["min_level"] == 0
    assert body["region"] is None


def test_create_fun_fact_with_region(client, scientist):
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": "gulf"}
    ).status_code == 201

    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "gulf fact", "fact": {"text": "hi"}, "region": region},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["region"] == region


def test_create_fun_fact_unknown_region_is_404(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "orphan fact", "fact": {}, "region": _new_uuid()},
    )
    assert resp.status_code == 404


def test_create_fun_fact_unique_title_conflicts(client, scientist):
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "dup", "fact": {}},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "dup", "fact": {}},
    )
    assert resp.status_code == 409


def test_update_fields(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "before", "fact": {"a": 1}, "min_level": 0},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "title": "after", "fact": {"a": 2}, "min_level": 4},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "after"
    assert body["fact"] == {"a": 2}
    assert body["min_level"] == 4


def test_update_explicit_null_on_title_fact_min_level_is_noop(client, scientist):
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "keep", "fact": {"a": 1}, "min_level": 3},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "title": None, "fact": None, "min_level": None},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "keep"
    assert body["fact"] == {"a": 1}
    assert body["min_level"] == 3


def test_update_sets_region(client, scientist):
    region = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": "north"})
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "regionless", "fact": {}},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "region": region},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["region"] == region


def test_update_explicit_null_clears_region(client, scientist):
    region = _new_uuid()
    client.post("/api/v1/dataset/regions/create", json={"uuid": region, "title": "south"})
    u = _new_uuid()
    client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": u, "title": "regioned", "fact": {}, "region": region},
    )
    resp = client.post(
        "/api/v1/dataset/fun-facts/update",
        json={"uuid": u, "region": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["region"] is None


def test_update_unknown_uuid_is_404(client, scientist):
    resp = client.post(
        "/api/v1/dataset/fun-facts/update", json={"uuid": _new_uuid(), "title": "x"}
    )
    assert resp.status_code == 404


def test_list_paginates(client, scientist):
    for i in range(5):
        client.post(
            "/api/v1/dataset/fun-facts/create",
            json={"uuid": _new_uuid(), "title": f"fact-{i}", "fact": {}},
        )
    resp = client.get("/api/v1/dataset/fun-facts?page=1&page_size=2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["fun_facts"]) == 2
    assert body["total"] == 5

    resp2 = client.get("/api/v1/dataset/fun-facts?page=3&page_size=2")
    assert len(resp2.json()["fun_facts"]) == 1


def test_fun_facts_role_gating_annotator_forbidden(client, seed_user, login_as):
    login_as(seed_user(username="ann", role="annotator"))
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={"uuid": _new_uuid(), "title": "t", "fact": {}},
    )
    assert resp.status_code == 403

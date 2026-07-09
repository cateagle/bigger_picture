import base64
import io
import uuid

import pytest
from PIL import Image as PILImage
from sqlalchemy import text


def _new_uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def scientist(seed_user, login_as):
    user = seed_user(username="sci", role="scientist")
    login_as(user)
    return user


def _create_fact(client, *, title, min_level=0, region=None):
    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={
            "uuid": _new_uuid(),
            "title": title,
            "fact": {"text": title},
            "min_level": min_level,
            **({"region": region} if region is not None else {}),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["uuid"]


def _seen_count(client, user_uuid: str, fact_uuid: str) -> int | None:
    engine = client.app.state.engine
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT sf.seen_count FROM seen_facts sf "
                "JOIN users u ON u.id = sf.user_id "
                "JOIN fun_facts f ON f.id = sf.fact_id "
                "WHERE u.uuid = :u AND f.uuid = :f"
            ),
            {"u": uuid.UUID(user_uuid).bytes, "f": uuid.UUID(fact_uuid).bytes},
        ).fetchone()
        return row[0] if row else None


def test_random_returns_eligible_fact_and_records_seen(client, scientist, seed_user, login_as):
    fact = _create_fact(client, title="one")
    annotator = seed_user(username="ann", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 1})
    assert resp.status_code == 200, resp.text
    assert resp.json()["uuid"] == fact

    annotator_uuid = str(uuid.UUID(bytes=annotator.uuid))
    assert _seen_count(client, annotator_uuid, fact) == 1


def test_random_increments_seen_count_on_repeat(client, scientist, seed_user, login_as):
    fact = _create_fact(client, title="repeat")
    annotator = seed_user(username="ann2", role="annotator", expert_level=0)
    login_as(annotator)
    annotator_uuid = str(uuid.UUID(bytes=annotator.uuid))

    assert client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 2}).status_code == 200
    assert _seen_count(client, annotator_uuid, fact) == 1

    assert client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 2}).status_code == 200
    assert _seen_count(client, annotator_uuid, fact) == 2

    # seen_count (2) is no longer < max_seen (2) -> no longer eligible.
    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 2})
    assert resp.status_code == 404


def test_random_excludes_fact_above_min_level(client, scientist, seed_user, login_as):
    _create_fact(client, title="advanced", min_level=5)
    annotator = seed_user(username="ann3", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 1})
    assert resp.status_code == 404


def test_random_includes_fact_at_or_below_min_level(client, scientist, seed_user, login_as):
    fact = _create_fact(client, title="beginner", min_level=2)
    annotator = seed_user(username="ann4", role="annotator", expert_level=2)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 1})
    assert resp.status_code == 200
    assert resp.json()["uuid"] == fact


def test_random_region_scoped_fact_excluded_without_region(client, scientist, seed_user, login_as):
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": "reef"}
    ).status_code == 201
    _create_fact(client, title="reef-only", region=region)

    annotator = seed_user(username="ann5", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 1})
    assert resp.status_code == 404


def test_random_region_scoped_fact_included_with_matching_region(client, scientist, seed_user, login_as):
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": "lagoon"}
    ).status_code == 201
    fact = _create_fact(client, title="lagoon-only", region=region)

    annotator = seed_user(username="ann6", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get(
        "/api/v1/annotate/fun-facts/random", params={"max_seen": 1, "region": region}
    )
    assert resp.status_code == 200
    assert resp.json()["uuid"] == fact


def test_random_global_fact_included_regardless_of_region_filter(client, scientist, seed_user, login_as):
    region = _new_uuid()
    assert client.post(
        "/api/v1/dataset/regions/create", json={"uuid": region, "title": "atoll"}
    ).status_code == 201
    fact = _create_fact(client, title="global")

    annotator = seed_user(username="ann7", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get(
        "/api/v1/annotate/fun-facts/random", params={"max_seen": 1, "region": region}
    )
    assert resp.status_code == 200
    assert resp.json()["uuid"] == fact


def test_random_unknown_region_is_404(client, scientist, seed_user, login_as):
    _create_fact(client, title="whatever")
    annotator = seed_user(username="ann8", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get(
        "/api/v1/annotate/fun-facts/random", params={"max_seen": 1, "region": _new_uuid()}
    )
    assert resp.status_code == 404


def test_random_surfaces_attached_image(client, scientist, seed_user, login_as):
    img = PILImage.new("RGB", (10, 10), (5, 6, 7))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    resp = client.post(
        "/api/v1/dataset/fun-facts/create",
        json={
            "uuid": _new_uuid(), "title": "illustrated", "fact": {"text": "illustrated"},
            "image": image_b64, "image_filename": "pic.png",
        },
    )
    assert resp.status_code == 201, resp.text
    fact = resp.json()["uuid"]

    annotator = seed_user(username="ann11", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 1})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["uuid"] == fact
    assert body["image"] is not None
    assert body["image"]["filename"] == "pic.png"


def test_random_missing_max_seen_is_422(client, scientist, seed_user, login_as):
    _create_fact(client, title="needs-max-seen")
    annotator = seed_user(username="ann9", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random")
    assert resp.status_code == 422


def test_random_no_facts_is_404(client, seed_user, login_as):
    annotator = seed_user(username="ann10", role="annotator", expert_level=0)
    login_as(annotator)

    resp = client.get("/api/v1/annotate/fun-facts/random", params={"max_seen": 1})
    assert resp.status_code == 404

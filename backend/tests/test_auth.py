from src import config


def test_signup_creates_annotator_and_sets_cookie(client):
    response = client.post("/api/v1/auth/signup", json={"username": "alice"})
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["role"] == "annotator"
    assert body["expert_level"] == 0
    assert body["exp"] == 0
    assert config.COOKIE_NAME in response.cookies


def test_signup_duplicate_username_conflicts(client):
    client.post("/api/v1/auth/signup", json={"username": "bob"})
    response = client.post("/api/v1/auth/signup", json={"username": "bob"})
    assert response.status_code == 409


def test_signup_duplicate_username_case_insensitive(client):
    client.post("/api/v1/auth/signup", json={"username": "Carl"})
    response = client.post("/api/v1/auth/signup", json={"username": "carl"})
    assert response.status_code == 409


def test_login_existing_user_sets_cookie_and_resolves_identity(client):
    signup_response = client.post("/api/v1/auth/signup", json={"username": "frank"})
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

    login_response = client.post("/api/v1/auth/login", json={"username": "frank"})
    assert login_response.status_code == 200
    assert config.COOKIE_NAME in login_response.cookies
    assert login_response.json()["uuid"] == signup_response.json()["uuid"]
    assert client.get("/api/v1/auth/me").json()["username"] == "frank"


def test_login_is_case_insensitive(client):
    client.post("/api/v1/auth/signup", json={"username": "Grace"})
    client.post("/api/v1/auth/logout")

    login_response = client.post("/api/v1/auth/login", json={"username": "grace"})
    assert login_response.status_code == 200
    assert login_response.json()["username"] == "Grace"


def test_login_unknown_username_is_404(client):
    response = client.post("/api/v1/auth/login", json={"username": "nobody"})
    assert response.status_code == 404


def test_me_without_cookie_is_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_resolves_signed_up_identity(client):
    signup_response = client.post("/api/v1/auth/signup", json={"username": "dana"})
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "dana"
    assert me_response.json()["uuid"] == signup_response.json()["uuid"]


def test_me_with_garbage_cookie_is_401(client):
    client.cookies.set(config.COOKIE_NAME, "not-a-valid-uuid")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_clears_cookie(client):
    client.post("/api/v1/auth/signup", json={"username": "erin"})
    assert client.get("/api/v1/auth/me").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_story_defaults_to_null(client):
    client.post("/api/v1/auth/signup", json={"username": "story-default"})
    response = client.get("/api/v1/auth/story")
    assert response.status_code == 200
    assert response.json() == {"story": None}


def test_story_round_trips_arbitrary_json(client):
    client.post("/api/v1/auth/signup", json={"username": "story-writer"})
    payload = {"chapter": 3, "flags": ["met_octopus"], "done": False}
    response = client.post("/api/v1/auth/story", json={"story": payload})
    assert response.status_code == 200
    assert response.json() == {"story": payload}

    response = client.get("/api/v1/auth/story")
    assert response.status_code == 200
    assert response.json() == {"story": payload}


def test_story_explicit_null_clears_it(client):
    client.post("/api/v1/auth/signup", json={"username": "story-clearer"})
    client.post("/api/v1/auth/story", json={"story": {"chapter": 1}})
    response = client.post("/api/v1/auth/story", json={"story": None})
    assert response.status_code == 200
    assert response.json() == {"story": None}


def test_story_is_per_user(client):
    client.post("/api/v1/auth/signup", json={"username": "story-a"})
    client.post("/api/v1/auth/story", json={"story": {"owner": "a"}})
    client.post("/api/v1/auth/logout")

    client.post("/api/v1/auth/signup", json={"username": "story-b"})
    response = client.get("/api/v1/auth/story")
    assert response.status_code == 200
    assert response.json() == {"story": None}


def test_story_without_cookie_is_401(client):
    response = client.get("/api/v1/auth/story")
    assert response.status_code == 401
    response = client.post("/api/v1/auth/story", json={"story": {}})
    assert response.status_code == 401


def test_login_annotator_without_password_still_succeeds(client):
    client.post("/api/v1/auth/signup", json={"username": "plain-annotator"})
    client.post("/api/v1/auth/logout")
    resp = client.post("/api/v1/auth/login", json={"username": "plain-annotator"})
    assert resp.status_code == 200


def test_login_annotator_with_extraneous_password_is_still_ignored(client):
    client.post("/api/v1/auth/signup", json={"username": "annotator-with-pw-field"})
    client.post("/api/v1/auth/logout")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "annotator-with-pw-field", "password": "whatever"}
    )
    assert resp.status_code == 200


def test_login_scientist_missing_password_is_401(client, seed_user, login_as):
    seed_user(username="sci", role="scientist")
    resp = client.post("/api/v1/auth/login", json={"username": "sci"})
    assert resp.status_code == 401


def test_login_scientist_without_stored_credential_is_401(client, seed_user):
    seed_user(username="sci-nopw", role="scientist")
    resp = client.post("/api/v1/auth/login", json={"username": "sci-nopw", "password": "anything1234"})
    assert resp.status_code == 401


def test_login_scientist_wrong_password_is_401(client, seed_user, set_password):
    sci = seed_user(username="sci2", role="scientist")
    set_password(sci, "correct horse battery staple")
    resp = client.post("/api/v1/auth/login", json={"username": "sci2", "password": "wrong password here"})
    assert resp.status_code == 401


def test_login_scientist_correct_password_succeeds_and_sets_cookie(client, seed_user, set_password):
    sci = seed_user(username="sci3", role="scientist")
    set_password(sci, "correct horse battery staple")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "sci3", "password": "correct horse battery staple"}
    )
    assert resp.status_code == 200
    assert config.COOKIE_NAME in resp.cookies


def test_login_admin_correct_password_succeeds(client, seed_user, set_password):
    admin = seed_user(username="admin2", role="admin")
    set_password(admin, "correct horse battery staple")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin2", "password": "correct horse battery staple"}
    )
    assert resp.status_code == 200


def test_login_unknown_username_is_404_even_with_password_supplied(client):
    resp = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "whatever12"})
    assert resp.status_code == 404


def test_set_password_requires_authentication(client):
    resp = client.post("/api/v1/auth/password", json={"password": "correct horse battery staple"})
    assert resp.status_code == 401


def test_set_password_rejected_for_annotator(client):
    client.post("/api/v1/auth/signup", json={"username": "annotator-no-pw"})
    resp = client.post("/api/v1/auth/password", json={"password": "correct horse battery staple"})
    assert resp.status_code == 403


def test_set_password_too_short_is_422(client, seed_user, login_as):
    sci = seed_user(username="sci4", role="scientist")
    login_as(sci)
    resp = client.post("/api/v1/auth/password", json={"password": "short"})
    assert resp.status_code == 422


def test_set_password_too_long_is_422(client, seed_user, login_as):
    sci = seed_user(username="sci5", role="scientist")
    login_as(sci)
    resp = client.post("/api/v1/auth/password", json={"password": "x" * 128})
    assert resp.status_code == 422


def test_set_password_then_login_with_new_password_succeeds(client, seed_user, login_as):
    sci = seed_user(username="sci6", role="scientist")
    login_as(sci)
    resp = client.post("/api/v1/auth/password", json={"password": "brand new password"})
    assert resp.status_code == 204

    client.post("/api/v1/auth/logout")
    login_resp = client.post("/api/v1/auth/login", json={"username": "sci6", "password": "brand new password"})
    assert login_resp.status_code == 200


def test_set_password_invalidates_old_password(client, seed_user, login_as, set_password):
    sci = seed_user(username="sci7", role="scientist")
    set_password(sci, "old password value")
    login_as(sci)
    client.post("/api/v1/auth/password", json={"password": "brand new password"})

    client.post("/api/v1/auth/logout")
    old_login = client.post("/api/v1/auth/login", json={"username": "sci7", "password": "old password value"})
    assert old_login.status_code == 401

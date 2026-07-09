from src.password_auth.hashing import hash_password, verify_password
from src.password_auth.store import delete_password_hash, get_password_hash, has_password, set_password_hash


def test_hash_password_produces_argon2_phc_string():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")


def test_verify_password_accepts_correct_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password here", hashed) is False


def test_verify_password_rejects_garbage_hash():
    assert verify_password("whatever", "not-a-real-hash") is False


def test_set_and_get_password_hash_roundtrip(tmp_path):
    db_path = str(tmp_path / "auth.db")
    user_uuid = b"0" * 16
    set_password_hash(db_path, user_uuid, "some-hash-value")
    assert get_password_hash(db_path, user_uuid) == "some-hash-value"


def test_get_password_hash_returns_none_when_absent(tmp_path):
    db_path = str(tmp_path / "auth.db")
    assert get_password_hash(db_path, b"1" * 16) is None


def test_has_password_reflects_presence(tmp_path):
    db_path = str(tmp_path / "auth.db")
    user_uuid = b"2" * 16
    assert has_password(db_path, user_uuid) is False
    set_password_hash(db_path, user_uuid, "some-hash-value")
    assert has_password(db_path, user_uuid) is True


def test_set_password_hash_upserts_existing_row(tmp_path):
    db_path = str(tmp_path / "auth.db")
    user_uuid = b"3" * 16
    set_password_hash(db_path, user_uuid, "first-hash")
    set_password_hash(db_path, user_uuid, "second-hash")
    assert get_password_hash(db_path, user_uuid) == "second-hash"


def test_delete_password_hash_is_idempotent_when_absent(tmp_path):
    db_path = str(tmp_path / "auth.db")
    delete_password_hash(db_path, b"4" * 16)  # must not raise
    assert get_password_hash(db_path, b"4" * 16) is None


def test_delete_password_hash_removes_existing_row(tmp_path):
    db_path = str(tmp_path / "auth.db")
    user_uuid = b"5" * 16
    set_password_hash(db_path, user_uuid, "some-hash-value")
    delete_password_hash(db_path, user_uuid)
    assert get_password_hash(db_path, user_uuid) is None

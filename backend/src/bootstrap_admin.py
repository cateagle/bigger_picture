"""One-off script to create the very first admin user.

Self-service signup (POST /api/v1/auth/signup) always forces role='annotator',
so there is no way to obtain the first admin through the API. Run this once
against a fresh database:

    cd backend && devenv shell -- python -m src.bootstrap_admin --username admin --password <10-127 chars>

If --password is omitted, the admin is created without one - the printed uuid
is then their only credential (no recovery mechanism); set it as the
`session_uuid` cookie to authenticate as this user, and use
POST /api/v1/auth/password once logged in to set a password afterward.
"""

import argparse
import logging

from sqlalchemy.engine import Engine

from src import config
from src.constants import Role
from src.db import make_engine, make_session_factory
from src.migrations.runner import run_migrations
from src.password_auth.hashing import hash_password
from src.password_auth.store import has_any_password, set_password_hash
from src.schema.users import User, count_users, create_self_referencing_user, lookup_user_by_username


def bootstrap_admin(engine: Engine, username: str, expert_level: int = 0, password: str | None = None) -> User:
    if count_users(engine) > 0:
        raise RuntimeError("users table is not empty; refusing to bootstrap a second self-referencing admin")
    user = create_self_referencing_user(engine, username=username, role=Role.ADMIN, expert_level=expert_level)
    if password is not None:
        set_password_hash(config.AUTH_DATABASE_PATH, user.uuid, hash_password(password))
    return user


def seed_admin_from_env(engine: Engine, auth_database_path: str) -> User | None:
    """Create the seed admin configured via SEED_ADMIN_USERNAME, if any, and/or
    give them a password the first time the password_auth database is used.

    Called on startup once both schemas exist. Two independent, idempotent
    behaviors, both safe to run on every boot:

    - User creation: does nothing if no username is configured, or if the
      users table is already populated (so an existing database is never
      touched, and the admin is not re-created after being renamed/deleted).
    - Password seeding: does nothing once the password_auth database already
      has a stored credential for *anyone* - this is what makes it safe to
      run unconditionally, and covers activating password auth later against
      a database that already had an admin (no user creation needed, just a
      password) without ever overwriting a password an admin has since
      changed. SEED_ADMIN_PASSWORD has a non-blank default specifically so
      this never leaves an admin without a way to log in that requires a
      manual CLI step - set it to an explicit empty string to opt out.
    """
    username = config.SEED_ADMIN_USERNAME.strip()
    if not username:
        return None

    user = None
    if count_users(engine) == 0:
        user = create_self_referencing_user(
            engine, username=username, role=Role.ADMIN, expert_level=config.SEED_ADMIN_EXPERT_LEVEL
        )
        logging.getLogger(__name__).info("Seeded admin user %r (id=%s) from SEED_ADMIN_USERNAME", username, user.id)

    password = config.SEED_ADMIN_PASSWORD.strip()
    if password and not has_any_password(auth_database_path):
        if user is None:
            with make_session_factory(engine)() as session:
                user = lookup_user_by_username(session, username)
        if user is not None:
            set_password_hash(auth_database_path, user.uuid, hash_password(password))
            logging.getLogger(__name__).info(
                "Seeded password for admin user %r from SEED_ADMIN_PASSWORD - change it via "
                "POST /api/v1/auth/password if this used the default fallback value",
                username,
            )

    return user


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the first admin user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--expert-level", type=int, default=0)
    parser.add_argument("--password", default=None, help="Optional password, 10-127 characters")
    parser.add_argument("--database-path", default=config.DATABASE_PATH)
    args = parser.parse_args()

    if args.password is not None:
        from src.password_auth.hashing import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

        if not (MIN_PASSWORD_LENGTH <= len(args.password) <= MAX_PASSWORD_LENGTH):
            parser.error(f"--password must be {MIN_PASSWORD_LENGTH}-{MAX_PASSWORD_LENGTH} characters")

    run_migrations(args.database_path)
    engine = make_engine(args.database_path)
    user = bootstrap_admin(engine, args.username, args.expert_level, args.password)

    print(f"Created admin '{args.username}' (id={user.id})")
    print(f"uuid (hex) = {config.encode_uuid(user.uuid)}")
    if args.password is not None:
        print("A password was set - log in normally via POST /api/v1/auth/login.")
    else:
        print(f"Set this as the '{config.COOKIE_NAME}' cookie to authenticate as this admin.")

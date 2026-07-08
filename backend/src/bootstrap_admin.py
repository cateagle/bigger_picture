"""One-off script to create the very first admin user.

Self-service signup (POST /api/v1/auth/signup) always forces role='annotator',
so there is no way to obtain the first admin through the API. Run this once
against a fresh database:

    cd backend && devenv shell -- python -m src.bootstrap_admin --username admin

The printed uuid is the admin's only credential (there is no password and no
recovery mechanism) - save it and set it as the `session_uuid` cookie to
authenticate as this user.
"""

import argparse
import logging

from sqlalchemy.engine import Engine

from src import config
from src.constants import Role
from src.db import make_engine
from src.migrations.runner import run_migrations
from src.schema.users import User, count_users, create_self_referencing_user


def bootstrap_admin(engine: Engine, username: str, expert_level: int = 0) -> User:
    if count_users(engine) > 0:
        raise RuntimeError("users table is not empty; refusing to bootstrap a second self-referencing admin")
    return create_self_referencing_user(engine, username=username, role=Role.ADMIN, expert_level=expert_level)


def seed_admin_from_env(engine: Engine) -> User | None:
    """Create the seed admin configured via SEED_ADMIN_USERNAME, if any.

    Called on startup once the schema exists. Idempotent and safe to run on
    every boot: does nothing if no username is configured or if the users
    table is already populated (so an existing database is never touched, and
    the admin is not re-created after it has been renamed or deleted).
    """
    username = config.SEED_ADMIN_USERNAME.strip()
    if not username:
        return None
    if count_users(engine) > 0:
        return None

    user = create_self_referencing_user(
        engine, username=username, role=Role.ADMIN, expert_level=config.SEED_ADMIN_EXPERT_LEVEL
    )
    logging.getLogger(__name__).info("Seeded admin user %r (id=%s) from SEED_ADMIN_USERNAME", username, user.id)
    return user


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the first admin user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--expert-level", type=int, default=0)
    parser.add_argument("--database-path", default=config.DATABASE_PATH)
    args = parser.parse_args()

    run_migrations(args.database_path)
    engine = make_engine(args.database_path)
    user = bootstrap_admin(engine, args.username, args.expert_level)

    print(f"Created admin '{args.username}' (id={user.id})")
    print(f"uuid (hex) = {config.encode_uuid(user.uuid)}")
    print(f"Set this as the '{config.COOKIE_NAME}' cookie to authenticate as this admin.")

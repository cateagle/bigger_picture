"""Script to create an admin and a scientist user in an already-in-use database.

Unlike `bootstrap_admin.py` (which only ever creates the very first,
self-referencing admin and refuses if the users table is non-empty), this is
for adding more privileged users - e.g. to a database that already has
annotators, or even an admin - once self-service signup (always `annotator`)
isn't enough. Run against any database, any number of times:

    cd backend && devenv shell -- python -m src.create_users --admin-username admin --scientist-username scientist

Like `bootstrap_admin.py`, there's no session/cookie to attribute creation to
(this runs out-of-band, not through the API), so created users are
self-referencing. Skips (rather than errors on) any username that's already
taken, so it's safe to re-run with the same arguments.
"""

import argparse
import sqlite3

from sqlalchemy.engine import Engine

from src import config
from src.constants import Role
from src.db import make_engine
from src.migrations.runner import run_migrations
from src.schema.users import User, create_self_referencing_user


def create_user_if_missing(engine: Engine, *, username: str, role: str, expert_level: int = 0) -> User | None:
    """Create a self-referencing user, or return `None` if `username` is already taken."""
    try:
        return create_self_referencing_user(engine, username=username, role=role, expert_level=expert_level)
    except sqlite3.IntegrityError:
        return None


def seed_admin_and_scientist(
    engine: Engine,
    *,
    admin_username: str = "admin",
    scientist_username: str = "scientist",
    expert_level: int = 0,
) -> dict[str, User | None]:
    """Create an admin and a scientist user, regardless of how many users already exist.

    Each entry in the returned dict is `None` if that username was already
    taken (left untouched), so callers can tell created from skipped.
    """
    return {
        "admin": create_user_if_missing(engine, username=admin_username, role=Role.ADMIN, expert_level=expert_level),
        "scientist": create_user_if_missing(
            engine, username=scientist_username, role=Role.SCIENTIST, expert_level=expert_level
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin and a scientist user, even in a non-empty database")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--scientist-username", default="scientist")
    parser.add_argument("--expert-level", type=int, default=0)
    parser.add_argument("--database-path", default=config.DATABASE_PATH)
    args = parser.parse_args()

    run_migrations(args.database_path)
    engine = make_engine(args.database_path)
    created = seed_admin_and_scientist(
        engine,
        admin_username=args.admin_username,
        scientist_username=args.scientist_username,
        expert_level=args.expert_level,
    )

    for label, user in created.items():
        if user is None:
            print(f"{label}: username already taken, skipped")
        else:
            print(f"{label}: created '{user.username}' (id={user.id})")
            print(f"  uuid (hex) = {config.encode_uuid(user.uuid)}")

    print(f"Set a uuid (hex) above as the '{config.COOKIE_NAME}' cookie to authenticate as that user.")

"""Stateless CSRF protection for scientist/admin sessions.

Annotator accounts are exempt (see AuthMiddleware) - self-service annotator
signup/annotation is low-value enough that this isn't worth the UX cost, and
those accounts have no password to protect. Scientist/admin sessions can
create/promote/demote users, change their own password, and manage backups,
so a forged cross-site request against one of those accounts is worth
protecting against.

Uses the "signed double-submit cookie" pattern: the token is
HMAC-SHA256(CSRF_SECRET, user_uuid), deterministic and unstored. The frontend
reads it from a non-httponly cookie and echoes it back via the X-CSRF-Token
header on state-changing requests; the server recomputes and compares against
the header (not the cookie) so a bare ability to set a same-origin cookie
isn't enough to forge a valid token - the secret is required.
"""

import hmac

from src import config

CSRF_HEADER_NAME = "X-CSRF-Token"


def compute_csrf_token(user_uuid: bytes) -> str:
    return hmac.new(config.CSRF_SECRET, user_uuid, "sha256").hexdigest()


def verify_csrf_token(user_uuid: bytes, candidate: str | None) -> bool:
    if not candidate:
        return False
    return hmac.compare_digest(compute_csrf_token(user_uuid), candidate)

from sqlalchemy.orm import Session

from src.schema.users import User


def grant_exp(db: Session, user: User, amount: int) -> None:
    """Add `amount` to a user's exp. Does not commit.

    The `trg_update_expert_level` DB trigger derives `expert_level` from the
    new total automatically once this change is committed.
    """
    user.exp += amount

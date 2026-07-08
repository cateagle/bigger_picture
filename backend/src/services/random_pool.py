import random

from sqlalchemy import Select
from sqlalchemy.orm import Session

from src import config


def sample_pool(db: Session, stmt: Select, n: int) -> list:
    pool_size = max(n, config.NEXT_ITEM_POOL_SIZE)
    pool = db.execute(stmt.limit(pool_size)).scalars().all()
    return random.sample(pool, min(n, len(pool)))

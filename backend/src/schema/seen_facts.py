from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class SeenFact(Base):
    __tablename__ = "seen_facts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey("fun_facts.id"), primary_key=True)
    seen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

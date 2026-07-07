from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class PairStatusRow(Base):
    __tablename__ = "pair_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

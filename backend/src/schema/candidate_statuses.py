from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class CandidateStatusRow(Base):
    __tablename__ = "candidate_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

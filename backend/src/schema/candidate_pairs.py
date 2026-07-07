from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class CandidatePair(Base):
    __tablename__ = "candidate_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    image1_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    image2_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_statuses.id"), nullable=False)
    reviewed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

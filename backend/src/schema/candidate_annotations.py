from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class CandidateAnnotation(Base):
    __tablename__ = "candidate_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_pairs.id"), nullable=False)
    no_overlap: Mapped[bool] = mapped_column(Boolean, nullable=False)
    expert_level: Mapped[int] = mapped_column(Integer, nullable=False)
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey("annotation_statuses.id"), nullable=False)
    reviewed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

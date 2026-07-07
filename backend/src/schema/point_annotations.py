from sqlalchemy import Float, ForeignKey, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class PointAnnotation(Base):
    __tablename__ = "point_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    pair_id: Mapped[int] = mapped_column(Integer, ForeignKey("image_pairs.id"), nullable=False)
    label_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("labels.id"), nullable=True)
    x1: Mapped[int] = mapped_column(Integer, nullable=False)
    y1: Mapped[int] = mapped_column(Integer, nullable=False)
    x2: Mapped[int] = mapped_column(Integer, nullable=False)
    y2: Mapped[int] = mapped_column(Integer, nullable=False)
    expert_level: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_id: Mapped[int] = mapped_column(Integer, ForeignKey("annotation_statuses.id"), nullable=False)
    reviewed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

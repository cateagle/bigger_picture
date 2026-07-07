from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class ImagePair(Base):
    __tablename__ = "image_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    image1_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    image2_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id"), nullable=False)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pair_statuses.id"), nullable=True)

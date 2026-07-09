from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class HelperImage(Base):
    __tablename__ = "helper_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    filepath: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    blake3_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

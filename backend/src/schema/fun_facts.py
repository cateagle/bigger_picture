from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class FunFact(Base):
    __tablename__ = "fun_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    fact_json: Mapped[str] = mapped_column(String, nullable=False)
    min_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), nullable=True)

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class QuestClaim(Base):
    __tablename__ = "quest_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    quest_key: Mapped[str] = mapped_column(Text, nullable=False)
    day_start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_exp: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.schema.base import Base


class FieldDocumentation(Base):
    __tablename__ = "field_documentation"

    table_name: Mapped[str] = mapped_column(String, primary_key=True)
    column_name: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

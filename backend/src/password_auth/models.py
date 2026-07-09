from sqlalchemy import Integer, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Private declarative base, separate from src.schema.base.Base: this table
# lives in its own SQLite file (see config.AUTH_DATABASE_PATH) and has no
# relationship to any table in the main app database.
class Base(DeclarativeBase):
    pass


class PasswordCredential(Base):
    __tablename__ = "password_credentials"

    user_uuid: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

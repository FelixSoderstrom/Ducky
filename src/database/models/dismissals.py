from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Dismissal(Base, TimestampMixin):
    """Dismissal model representing dismissed warnings or suggestions."""

    __tablename__ = "dismissals"

    id: Mapped[int] = mapped_column(primary_key=True)
    old_version: Mapped[str] = mapped_column(String(50), nullable=False)
    new_version: Mapped[str] = mapped_column(String(50), nullable=False)
    warning: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)

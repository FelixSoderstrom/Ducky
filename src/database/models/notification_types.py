from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .configs import Config


class NotificationType(Base):
    """NotificationType model representing different types of notifications."""

    __tablename__ = "notification_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )

    # Relationships
    configs: Mapped[List["Config"]] = relationship(
        "Config", back_populates="notification_type"
    )

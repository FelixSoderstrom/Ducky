from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .projects import Project
    from .notification_types import NotificationType


class Config(Base, TimestampMixin):
    """Config model representing project notification configurations."""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False
    )
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("notification_types.id"), nullable=False
    )
    notification_sound: Mapped[str] = mapped_column(
        String(100), nullable=False, default="quack.wav"
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="configs"
    )
    notification_type: Mapped["NotificationType"] = relationship(
        "NotificationType", back_populates="configs"
    )

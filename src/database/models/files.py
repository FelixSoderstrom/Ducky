from datetime import datetime
from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .projects import Project


class File(Base, TimestampMixin):
    """File model representing files and directories in a project."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_dir: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=True)
    last_edit: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="files"
    )

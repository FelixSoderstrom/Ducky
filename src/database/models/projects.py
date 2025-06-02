from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING, Optional

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .files import File
    from .configs import Config


class Project(Base, TimestampMixin):
    """Project model representing a project with its configuration."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    anthropic_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    eleven_labs_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="project", cascade="all, delete-orphan"
    )
    configs: Mapped[List["Config"]] = relationship(
        "Config", back_populates="project", cascade="all, delete-orphan"
    )

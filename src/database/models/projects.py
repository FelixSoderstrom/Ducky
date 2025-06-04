from sqlalchemy import String, Float
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
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Chatterbox TTS voice settings
    voice_prompt_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Path to custom voice prompt audio file"
    )
    voice_exaggeration: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=0.5, comment="Voice exaggeration level (0.0-1.0)"
    )
    voice_cfg_weight: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=0.5, comment="Voice CFG weight (0.0-1.0)"
    )

    # Relationships
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="project", cascade="all, delete-orphan"
    )
    configs: Mapped[List["Config"]] = relationship(
        "Config", back_populates="project", cascade="all, delete-orphan"
    )

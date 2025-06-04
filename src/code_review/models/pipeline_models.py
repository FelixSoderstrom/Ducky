"""Core data structures for the code review pipeline."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PipelineResult(Enum):
    """Enum for pipeline execution results."""
    CONTINUE = "continue"
    CANCEL = "cancel"


@dataclass
class WarningMessage:
    """Structure for warning messages passed between agents."""
    title: str = ""
    severity: str = "medium"  # "low", "medium", "high", "critical"
    description: str = ""
    suggestions: List[str] = None
    affected_files: List[str] = None
    confidence: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.affected_files is None:
            self.affected_files = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PipelineOutput:
    """Final output structure from the pipeline."""
    notification: str
    warning: WarningMessage
    solution: str


@dataclass
class AgentContext:
    """Context passed to each agent containing all necessary information."""
    old_version: str
    new_version: str
    file_path: str
    project_id: int
    current_warning: Optional[WarningMessage] = None 
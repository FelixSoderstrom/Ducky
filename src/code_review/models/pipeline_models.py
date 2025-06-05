"""Core data structures for the code review pipeline."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PipelineResult(Enum):
    """Result types that agents can return."""
    CONTINUE = "continue"
    CANCEL = "cancel"


@dataclass
class WarningMessage:
    """Structure for warning messages passed between agents - designed for additive collaboration."""
    title: str = ""                                    # SET ONCE by InitialAssessment
    severity: str = "medium"                           # CAN BE MODIFIED by any agent ("low", "medium", "high", "critical")
    description: List[str] = field(default_factory=list)    # APPEND ONLY - each agent adds their perspective
    suggestions: List[str] = field(default_factory=list)    # APPEND ONLY - accumulated suggestions
    affected_files: List[str] = field(default_factory=list) # APPEND ONLY by InitialAssessment + ContextAwareness
    confidence: float = 0.0                           # CAN BE MODIFIED by any agent (0.0 to 1.0)
    metadata: List[Dict[str, Any]] = field(default_factory=list)  # APPEND ONLY - each agent adds their analysis
    
    def add_agent_analysis(self, agent_name: str, analysis_data: Dict[str, Any]) -> None:
        """Helper method to add agent-specific analysis to metadata."""
        self.metadata.append({
            "agent": agent_name,
            "timestamp": analysis_data.get("timestamp"),
            "reasoning": analysis_data.get("reasoning", ""),
            "confidence_impact": analysis_data.get("confidence_impact", 0.0),
            **analysis_data
        })
    
    def get_full_description(self) -> str:
        """Get concatenated description from all agents."""
        return " ".join(self.description)
    
    def get_agent_contributions(self) -> List[str]:
        """Get list of agents that have contributed to this warning."""
        return [meta.get("agent", "Unknown") for meta in self.metadata]


@dataclass
class PipelineOutput:
    """Final output structure from the pipeline - includes full context for RubberDuck."""
    notification: str
    warning: WarningMessage
    solution: str
    # New fields for RubberDuck context and RAG
    old_version: str
    new_version: str
    file_path: str
    project_id: int


@dataclass
class AgentContext:
    """Context passed to each agent during pipeline execution."""
    old_version: str
    new_version: str
    file_path: str
    project_id: int
    current_warning: WarningMessage = field(default_factory=WarningMessage) 
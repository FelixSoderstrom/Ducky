"""Protocol definitions for agent capabilities and interfaces."""

from typing import Protocol, List, Optional, runtime_checkable
from .pipeline_models import PipelineResult, WarningMessage, AgentContext


@runtime_checkable
class AgentCapabilities(Protocol):
    """Base protocol for all code review agents."""
    
    name: str
    agent_type: str
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """Analyze the code changes and return result with optional warning."""
        ...
    
    def should_process(self, context: AgentContext) -> bool:
        """Determine if this agent should process the given context."""
        ...


@runtime_checkable
class RAGCapable(Protocol):
    """Protocol for agents that need RAG (Retrieval-Augmented Generation) capabilities."""
    
    def query_dismissals(self) -> List:
        """Query all dismissed notifications from database."""
        ...
    
    def query_project_files(self, project_id: int, exclude_path: str = None) -> List:
        """Query files from the same project."""
        ...


@runtime_checkable 
class MCPCapable(Protocol):
    """Protocol for agents that need MCP (Model Context Protocol) server integration."""
    
    def query_documentation(self, query: str) -> str:
        """Query MCP server for documentation."""
        ... 
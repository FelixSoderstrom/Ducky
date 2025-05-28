from typing import Dict, Any, List, Optional, Protocol, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum
import logging
import json
from pathlib import Path

from src.watcher.compare_versions import FileChange
from src.database.session import get_db
from src.database.models import Dismissal, File, Project
from sqlalchemy import select


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


class CodeReviewAgent(ABC):
    """Abstract base class for all code review agents."""
    
    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"agent.{name}")
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from JSON file."""
        try:
            prompts_path = Path("src/code_review/utils/system_prompts.json")
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            return prompts.get(self.agent_type, "")
        except FileNotFoundError:
            self.logger.warning(f"System prompts file not found for {self.agent_type}")
            return ""
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in system prompts file")
            return ""
    
    @abstractmethod
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Analyze the code changes and warning message.
        
        Args:
            context: AgentContext containing changes and current warning
            
        Returns:
            Tuple of (PipelineResult, Optional[WarningMessage])
            - PipelineResult.CONTINUE: Continue to next agent with updated warning
            - PipelineResult.CANCEL: Cancel pipeline (no issue found)
        """
        pass
    
    def should_process(self, context: AgentContext) -> bool:
        """Override to add conditions for when this agent should run."""
        return True


class RAGCapableAgent(CodeReviewAgent):
    """Base class for agents that need RAG capabilities."""
    
    def query_dismissals(self) -> List[Dismissal]:
        """Query all dismissed notifications from database."""
        with get_db() as session:
            stmt = select(Dismissal)
            result = session.execute(stmt)
            return result.scalars().all()
    
    def query_project_files(self, project_id: int, exclude_path: str = None) -> List[File]:
        """Query files from the same project."""
        with get_db() as session:
            stmt = select(File).where(File.project_id == project_id)
            if exclude_path:
                stmt = stmt.where(File.path != exclude_path)
            result = session.execute(stmt)
            return result.scalars().all()


class MCPCapableAgent(CodeReviewAgent):
    """Base class for agents that need MCP server integration."""
    
    def query_documentation(self, query: str) -> str:
        """
        Query MCP server for documentation.
        
        Args:
            query: Documentation query string
            
        Returns:
            Documentation response or empty string if not available
        """
        # TODO: Implement MCP server integration
        # This is left open-ended for future implementation
        self.logger.info(f"MCP query: {query}")
        return ""


# Import the individual agent classes
from ..agents.initial_assessment import InitialAssessment
from ..agents.notification_assessment import NotificationAssessment  
from ..agents.context_awareness import ContextAwareness
from ..agents.syntax_validation import SyntaxValidation
from ..agents.notification_writer import NotificationWriter
from ..agents.code_writer import CodeWriter


class CodeReviewPipeline:
    """Main pipeline orchestrator for code review agents."""
    
    def __init__(self, api_key: str):
        self.agents = [
            InitialAssessment(api_key),
            NotificationAssessment(api_key),
            ContextAwareness(api_key),
            SyntaxValidation(api_key),
            NotificationWriter(api_key),
            CodeWriter(api_key)
        ]
        self.logger = logging.getLogger("pipeline")
    
    def execute(self, changes: List[FileChange], project_id: int) -> Optional[PipelineOutput]:
        """
        Execute the agent pipeline on the given code changes.
        
        Args:
            changes: List of FileChange objects
            project_id: ID of the project being analyzed
            
        Returns:
            PipelineOutput with notification, warning, and solution or None if cancelled
        """
        if not changes:
            return None
        
        # For now, process only the first change
        change = changes[0]
        
        self.logger.info(f"Starting pipeline for {change.file_path}")
        
        context = AgentContext(
            old_version=change.old_content or "",
            new_version=change.new_content or "",
            file_path=change.file_path,
            project_id=project_id
        )
        
        notification = ""
        solution = ""
        
        for i, agent in enumerate(self.agents):
            if not agent.should_process(context):
                self.logger.info(f"Skipping agent {agent.name} - conditions not met")
                continue
            
            self.logger.info(f"Running agent {i+1}/{len(self.agents)}: {agent.name}")
            
            try:
                if isinstance(agent, NotificationWriter):
                    result, notification = agent.analyze(context)
                elif isinstance(agent, CodeWriter):
                    result, solution = agent.analyze(context)
                else:
                    result, updated_warning = agent.analyze(context)
                    
                    if result == PipelineResult.CANCEL:
                        self.logger.info(f"Pipeline cancelled by {agent.name}")
                        return None
                    
                    context.current_warning = updated_warning
                
            except Exception as e:
                self.logger.error(f"Agent {agent.name} failed: {str(e)}")
                continue
        
        if context.current_warning:
            return PipelineOutput(
                notification=notification,
                warning=context.current_warning,
                solution=solution
            )
        
        return None


def code_review_pipeline(changes: List[FileChange], project_id: int) -> None:
    """Process code changes and generate review feedback using agent pipeline."""
    
    if not changes:
        return
    
    # Get API key from the project in database
    with get_db() as session:
        from sqlalchemy import select
        stmt = select(Project).where(Project.id == project_id)
        result = session.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            logging.error(f"Project {project_id} not found")
            return
        
        api_key = project.api_key
    
    pipeline = CodeReviewPipeline(api_key)
    result = pipeline.execute(changes, project_id)
    
    if result:
        _handle_pipeline_output(result)
    else:
        logging.info("No issues found - pipeline was cancelled")


def _handle_pipeline_output(output: PipelineOutput) -> None:
    """Handle the final pipeline output."""
    # TODO: Implement notification system integration
    # TODO: Save to database
    # TODO: Format for UI display
    
    logger = logging.getLogger("pipeline.output")
    logger.info(f"Notification: {output.notification}")
    logger.info(f"Warning: {output.warning.title}")
    logger.info(f"Solution: {output.solution}")
    
    # Also log to console for immediate feedback during development
    logger.debug(f"Pipeline output - Notification: {output.notification}")
    logger.debug(f"Pipeline output - Warning: {output.warning.title}")
    logger.debug(f"Pipeline output - Solution: {output.solution}")
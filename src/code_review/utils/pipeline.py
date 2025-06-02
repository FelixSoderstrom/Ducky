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

# Get the existing code review logger (don't create a new one)
cr_logger = logging.getLogger("code_review")

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
        self.logger = logging.getLogger(f"ducky.agent.{name}")  # Keep original logger for app-level logging
        self.cr_logger = cr_logger  # Code review specific logger
        self.system_prompt = self._load_system_prompt()
    
    def _log_warning_state(self, stage: str, warning: Optional[WarningMessage], decision: str = ""):
        """Log the current warning state to code review log."""
        if warning:
            self.cr_logger.info(f"[{stage}] Warning State:")
            self.cr_logger.info(f"  ├─ Title: {warning.title}")
            self.cr_logger.info(f"  ├─ Severity: {warning.severity} (Confidence: {warning.confidence:.2f})")
            self.cr_logger.info(f"  ├─ Description: {warning.description}")
            self.cr_logger.info(f"  ├─ Suggestions: {len(warning.suggestions)} items")
            for i, suggestion in enumerate(warning.suggestions[:3], 1):  # Show first 3
                self.cr_logger.info(f"  │   {i}. {suggestion}")
            if len(warning.suggestions) > 3:
                self.cr_logger.info(f"  │   ... and {len(warning.suggestions) - 3} more")
            self.cr_logger.info(f"  └─ Metadata: {list(warning.metadata.keys())}")
        else:
            self.cr_logger.info(f"[{stage}] No warning message")
        
        if decision:
            self.cr_logger.info(f"[{stage}] Decision: {decision}")
    
    def _log_llm_output(self, stage: str, output: str, truncate: int = 500):
        """Log LLM output to code review log."""
        if len(output) > truncate:
            truncated = output[:truncate] + f"... [truncated, full length: {len(output)} chars]"
        else:
            truncated = output
        
        self.cr_logger.info(f"[{stage}] LLM Output:")
        self.cr_logger.info(f"  {truncated}")
    
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
        
        # Log file information to code review log
        cr_logger.info("=" * 80)
        cr_logger.info(f"CODE REVIEW PIPELINE STARTING")
        cr_logger.info("=" * 80)
        cr_logger.info(f"File: {change['path']}")
        cr_logger.info(f"Project ID: {project_id}")
        cr_logger.info(f"Is New File: {change.get('is_new_file', False)}")
        cr_logger.info(f"Last Edit: {change.get('last_edit', 'Unknown')}")
        cr_logger.info("-" * 80)
        
        self.logger.info(f"Starting pipeline for {change['path']}")
        
        # Validate that we have meaningful content to analyze
        old_version = change.get('old_version', "")
        new_version = change.get('new_version', "")
        
        if not old_version and not new_version:
            cr_logger.warning(f"No content found for file {change['path']} - skipping pipeline")
            self.logger.warning(f"No content found for file {change['path']} - skipping pipeline")
            return None
        
        # For new files, old_version can be empty, but new_version should have content
        if change.get('is_new_file', False) and not new_version.strip():
            cr_logger.warning(f"New file {change['path']} has no content - skipping pipeline")
            self.logger.warning(f"New file {change['path']} has no content - skipping pipeline")
            return None
        
        # For existing files, we should have both versions (unless it's a deletion)
        if not change.get('is_new_file', False) and not old_version and not new_version:
            cr_logger.warning(f"No content versions found for {change['path']} - skipping pipeline")
            self.logger.warning(f"No content versions found for {change['path']} - skipping pipeline") 
            return None
        
        # Log content preview
        cr_logger.info(f"Content Analysis:")
        cr_logger.info(f"  ├─ Old Version: {len(old_version)} characters")
        if old_version:
            preview_old = old_version[:200].replace('\n', '\\n')
            ellipsis = '...' if len(old_version) > 200 else ''
            cr_logger.info(f"  │   Preview: {preview_old}{ellipsis}")
        cr_logger.info(f"  └─ New Version: {len(new_version)} characters")
        if new_version:
            preview_new = new_version[:200].replace('\n', '\\n')
            ellipsis = '...' if len(new_version) > 200 else ''
            cr_logger.info(f"      Preview: {preview_new}{ellipsis}")
        
        context = AgentContext(
            old_version=old_version,
            new_version=new_version,
            file_path=change['path'],
            project_id=project_id
        )
        
        notification = ""
        solution = ""
        
        for i, agent in enumerate(self.agents):
            if not agent.should_process(context):
                cr_logger.info(f"Skipping agent {agent.name} - conditions not met")
                self.logger.info(f"Skipping agent {agent.name} - conditions not met")
                continue
            
            cr_logger.info(f"\nAGENT {i+1}/{len(self.agents)}: {agent.name}")
            cr_logger.info("─" * 60)
            self.logger.info(f"Running agent {i+1}/{len(self.agents)}: {agent.name}")
            
            try:
                if isinstance(agent, NotificationWriter):
                    result, notification = agent.analyze(context)
                    cr_logger.info(f"[{agent.name}] Generated Notification:")
                    cr_logger.info(f"  {notification}")
                elif isinstance(agent, CodeWriter):
                    result, solution = agent.analyze(context)
                    cr_logger.info(f"[{agent.name}] Generated Solution:")
                    cr_logger.info(f"  Length: {len(solution)} characters")
                    # Show first few lines of solution
                    solution_lines = solution.split('\n')
                    for line in solution_lines[:5]:
                        cr_logger.info(f"  │ {line}")
                    if len(solution_lines) > 5:
                        remaining_lines = len(solution_lines) - 5
                        cr_logger.info(f"  └─ ... and {remaining_lines} more lines")
                else:
                    result, updated_warning = agent.analyze(context)
                    
                    if result == PipelineResult.CANCEL:
                        cr_logger.info(f"Pipeline cancelled by {agent.name}")
                        cr_logger.info(f"   Reason: Agent determined no further analysis needed")
                        self.logger.info(f"Pipeline cancelled by {agent.name}")
                        return None
                    
                    # Log warning state after agent processing
                    agent._log_warning_state(f"{agent.name} - OUTPUT", updated_warning, "CONTINUE")
                    context.current_warning = updated_warning
                
            except Exception as e:
                cr_logger.error(f"Agent {agent.name} failed: {str(e)}")
                cr_logger.error(f"   Context: file={context.file_path}")
                if context.current_warning:
                    cr_logger.error(f"   Current warning: {context.current_warning.title}")
                self.logger.error(f"Agent {agent.name} failed: {str(e)}")
                continue
        
        cr_logger.info("\n" + "=" * 80)
        cr_logger.info("PIPELINE COMPLETED")
        cr_logger.info("=" * 80)
        
        if context.current_warning:
            output = PipelineOutput(
                notification=notification,
                warning=context.current_warning,
                solution=solution
            )
            cr_logger.info(f"Pipeline successful - Generated complete output")
            return output
        
        cr_logger.warning(f"Pipeline completed but no warning message was generated")
        return None


async def code_review_pipeline(changes: List[FileChange], project_id: int) -> Optional[Dict[str, Any]]:
    """Process code changes and generate review feedback using agent pipeline."""
    
    if not changes:
        return None
    
    # Get API key from the project in database
    with get_db() as session:
        from sqlalchemy import select
        stmt = select(Project).where(Project.id == project_id)
        result = session.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            logging.error(f"Project {project_id} not found")
            return None
        
        api_key = project.anthropic_key
    
    # Run the pipeline in a thread pool to avoid blocking the event loop
    import asyncio
    import concurrent.futures
    
    def run_pipeline():
        pipeline = CodeReviewPipeline(api_key)
        return pipeline.execute(changes, project_id)
    
    # Execute pipeline in thread pool
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, run_pipeline)
    
    if result:
        return _handle_pipeline_output(result)
    else:
        logging.info("No issues found - pipeline was cancelled")
        return None


def _handle_pipeline_output(output: PipelineOutput) -> Dict[str, Any]:
    """
    Handle the final pipeline output and return it as a dictionary.
    
    Args:
        output: The PipelineOutput containing notification, warning, and solution
        
    Returns:
        Dictionary containing the pipeline response data
    """
    logger = logging.getLogger("pipeline.output")
    logger.info(f"Notification: {output.notification}")
    logger.info(f"Warning: {output.warning.title}")
    logger.info(f"Solution: {output.solution}")
    
    # Also log to console for immediate feedback during development
    logger.debug(f"Pipeline output - Notification: {output.notification}")
    logger.debug(f"Pipeline output - Warning: {output.warning.title}")
    logger.debug(f"Pipeline output - Solution: {output.solution}")
    
    # Convert to dictionary for notification system
    response = {
        "notification": output.notification,
        "warning": {
            "title": output.warning.title,
            "severity": output.warning.severity,
            "description": output.warning.description,
            "suggestions": output.warning.suggestions,
            "affected_files": output.warning.affected_files,
            "confidence": output.warning.confidence,
            "metadata": output.warning.metadata
        },
        "solution": output.solution
    }
    
    return response
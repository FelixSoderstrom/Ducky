"""Abstract base class for all code review agents."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from ...models.pipeline_models import PipelineResult, WarningMessage, AgentContext
from ...utils.prompt_loader import PromptLoader


class CodeReviewAgent(ABC):
    """Abstract base class for all code review agents."""
    
    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"ducky.agent.{name}")  # Keep original logger for app-level logging
        self.cr_logger = logging.getLogger("code_review")  # Code review specific logger
        self.system_prompt = PromptLoader.load_prompt(agent_type)
    
    def _log_warning_state(self, stage: str, warning: Optional[WarningMessage], decision: str = ""):
        """Log the current warning state to code review log."""
        if warning:
            self.cr_logger.info(f"[{stage}] {warning.title} | {warning.severity} | {len(warning.suggestions)} suggestions")
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
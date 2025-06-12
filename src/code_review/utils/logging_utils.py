"""Logging utilities for the code review pipeline."""

import logging
from typing import Optional, List

from ..models.pipeline_models import WarningMessage


class PipelineLogger:
    """Utilities for pipeline-specific logging."""
    
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.logger = logging.getLogger(f"ducky.agent.{stage_name}")
        self.cr_logger = logging.getLogger("code_review")
    
    def log_warning_state(self, stage: str, warning: Optional[WarningMessage], decision: str = ""):
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
    
    def log_llm_output(self, stage: str, output: str, truncate: int = 500):
        """Log LLM output to code review log."""
        if len(output) > truncate:
            truncated = output[:truncate] + f"... [truncated, full length: {len(output)} chars]"
        else:
            truncated = output
        
        self.cr_logger.info(f"[{stage}] LLM Output:")
        self.cr_logger.info(f"  {truncated}")
    
    def log_agent_start(self, agent_index: int, total_agents: int):
        """Log agent execution start."""
        self.cr_logger.info(f"\nAGENT {agent_index+1}/{total_agents}: {self.stage_name}")
        self.cr_logger.info("─" * 60)
        self.logger.info(f"Running agent {agent_index+1}/{total_agents}: {self.stage_name}")
    
    def log_agent_skip(self, reason: str = "conditions not met"):
        """Log agent being skipped."""
        self.cr_logger.info(f"Skipping agent {self.stage_name} - {reason}")
        self.logger.info(f"Skipping agent {self.stage_name} - {reason}")
    
    def log_agent_error(self, error: Exception, context_file: str, current_warning: Optional[WarningMessage] = None):
        """Log agent execution error."""
        self.cr_logger.error(f"Agent {self.stage_name} failed: {str(error)}")
        self.cr_logger.error(f"   Context: file={context_file}")
        if current_warning:
            self.cr_logger.error(f"   Current warning: {current_warning.title}")
        self.logger.error(f"Agent {self.stage_name} failed: {str(error)}")


class PipelineLoggingHelper:
    """Static helper methods for pipeline logging."""
    
    @staticmethod
    def log_pipeline_start(file_path: str, project_id: int):
        """Log pipeline execution start."""
        cr_logger = logging.getLogger("code_review")
        cr_logger.info("=" * 80)
        cr_logger.info(f"CODE REVIEW PIPELINE STARTING")
        cr_logger.info("=" * 80)
        cr_logger.info(f"File: {file_path}")
        cr_logger.info(f"Project ID: {project_id}")
        cr_logger.info("-" * 80)
    
    @staticmethod
    def log_pipeline_completion(success: bool):
        """Log pipeline completion."""
        cr_logger = logging.getLogger("code_review")
        cr_logger.info("\n" + "=" * 80)
        cr_logger.info("PIPELINE COMPLETED")
        cr_logger.info("=" * 80)
        
        if success:
            cr_logger.info(f"Pipeline successful - Generated complete output")
        else:
            cr_logger.warning(f"Pipeline completed but no warning message was generated")
    
    @staticmethod
    def log_pipeline_cancellation(agent_name: str, reason: str = "Agent determined no further analysis needed"):
        """Log pipeline cancellation."""
        cr_logger = logging.getLogger("code_review")
        logger = logging.getLogger("ducky.pipeline")
        
        cr_logger.info(f"Pipeline cancelled by {agent_name}")
        cr_logger.info(f"   Reason: {reason}")
        logger.info(f"Pipeline cancelled by {agent_name}") 
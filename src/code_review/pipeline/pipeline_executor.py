"""Main pipeline executor for code review agents."""

import logging
from typing import List, Optional

from ..models.pipeline_models import PipelineResult, PipelineOutput, AgentContext
from ..agents.base.agent_factory import AgentFactory
from ..agents.notification_writer import NotificationWriter
from ..agents.code_writer import CodeWriter
from .pipeline_context import PipelineContextManager
from ...watcher.compare_versions import FileChange

logger = logging.getLogger("ducky.pipeline.executor")
cr_logger = logging.getLogger("code_review")


class CodeReviewPipeline:
    """Main pipeline orchestrator for code review agents."""
    
    def __init__(self, api_key: str):
        self.agents = AgentFactory.create_pipeline_agents(api_key)
        self.logger = logger
        self.context_manager = PipelineContextManager()
    
    def execute(self, changes: List[FileChange], project_id: int) -> Optional[PipelineOutput]:
        """
        Execute the agent pipeline on the given code changes.
        
        Args:
            changes: List of FileChange objects
            project_id: ID of the project being analyzed
            
        Returns:
            PipelineOutput with notification, warning, solution AND full context or None if cancelled
        """
        # Create and validate context
        context = self.context_manager.create_context_from_changes(changes, project_id)
        if not context:
            return None
        
        self.logger.info(f"Starting pipeline for {context.file_path}")
        
        notification = ""
        solution = ""
        
        for i, agent in enumerate(self.agents):
            if not agent.should_process(context):
                cr_logger.info(f"Skipping agent {agent.name} - conditions not met")
                self.logger.info(f"Skipping agent {agent.name} - conditions not met")
                continue
            
            cr_logger.info(f"AGENT {i+1}/{len(self.agents)}: {agent.name}")
            self.logger.info(f"Running agent {i+1}/{len(self.agents)}: {agent.name}")
            
            try:
                # Handle special agent types that return different outputs
                if isinstance(agent, NotificationWriter):
                    result, notification = agent.analyze(context)
                    cr_logger.info(f"[{agent.name}] Generated Notification:")
                    cr_logger.info(f"  {notification}")
                elif isinstance(agent, CodeWriter):
                    result, solution = agent.analyze(context)
                    cr_logger.info(f"[{agent.name}] Generated Solution: {len(solution)} characters")
                else:
                    # Standard agent that returns warning message
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
        
        cr_logger.info("PIPELINE COMPLETED")
        
        if context.current_warning:
            # Include ALL context data for RubberDuck
            output = PipelineOutput(
                notification=notification,
                warning=context.current_warning,
                solution=solution,
                old_version=context.old_version,
                new_version=context.new_version,
                file_path=context.file_path,
                project_id=context.project_id
            )
            cr_logger.info(f"Pipeline successful")
            return output
        
        cr_logger.warning(f"Pipeline completed but no warning message was generated")
        return None 
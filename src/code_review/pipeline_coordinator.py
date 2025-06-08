import asyncio
import logging
from typing import Dict, Any, Optional, List, Set

from src.watcher.compare_versions import FileChange
from src.code_review.utils.pipeline import code_review_pipeline
from src.notifications import notify_user
from src.services.chat_state_service import get_chat_state_service

logger = logging.getLogger("ducky.code_review.pipeline_coordinator")


class PipelineCoordinator:
    """Coordinates code review pipeline execution with concurrency control."""
    
    def __init__(self, max_concurrent_pipelines: int = 1):
        self.max_concurrent_pipelines = max_concurrent_pipelines
        self.running_pipelines: Set[int] = set()  # Track running pipeline IDs
        self.chat_state_service = get_chat_state_service()  # Initialize chat state service
        self.logger = logger
        
    def is_pipeline_running(self, project_id: Optional[int] = None) -> bool:
        """Check if any pipeline is running, or if a specific project's pipeline is running.
        
        Args:
            project_id: If provided, check only for this project's pipeline
            
        Returns:
            True if pipeline(s) are running, False otherwise
        """
        if project_id is not None:
            return project_id in self.running_pipelines
        return len(self.running_pipelines) > 0
    
    def can_start_pipeline(self, project_id: int) -> bool:
        """Check if a new pipeline can be started for the given project.
        
        Args:
            project_id: ID of the project wanting to start a pipeline
            
        Returns:
            True if pipeline can start, False if blocked by running pipeline, capacity, or active chat
        """
        # Check if chat is active first
        if self.chat_state_service.is_chat_active():
            active_notification_id = self.chat_state_service.get_active_notification_id()
            self.logger.info(f"Pipeline blocked for project {project_id} - chat session active (notification: {active_notification_id})")
            return False
        
        # Don't start if this project already has a running pipeline
        if project_id in self.running_pipelines:
            self.logger.debug(f"Pipeline blocked for project {project_id} - already running")
            return False
            
        # Don't start if we're at max capacity
        if len(self.running_pipelines) >= self.max_concurrent_pipelines:
            self.logger.debug(f"Pipeline blocked for project {project_id} - at capacity ({len(self.running_pipelines)}/{self.max_concurrent_pipelines})")
            return False
        
        # All checks passed
        self.logger.debug(f"Pipeline can start for project {project_id} - all checks passed")
        return True
    
    async def execute_if_available(self, changes: List[FileChange], project_id: int, app) -> bool:
        """Execute pipeline if capacity is available.
        
        Args:
            changes: List of file changes to process
            project_id: ID of the project
            app: UI application instance for notifications
            
        Returns:
            True if pipeline was started, False if skipped due to capacity/chat/existing pipeline
        """
        # Log current state for debugging
        chat_status = self.chat_state_service.get_chat_status()
        self.logger.debug(f"Pipeline execution check for project {project_id}: "
                         f"chat_active={chat_status['is_active']}, "
                         f"active_notification={chat_status['active_notification_id']}, "
                         f"running_pipelines={len(self.running_pipelines)}, "
                         f"max_concurrent={self.max_concurrent_pipelines}")
        
        if not self.can_start_pipeline(project_id):
            # Detailed logging for why pipeline was blocked
            if self.chat_state_service.is_chat_active():
                active_notification_id = self.chat_state_service.get_active_notification_id()
                self.logger.info(f"Pipeline execution BLOCKED for project {project_id} - chat session active (notification: {active_notification_id})")
            elif project_id in self.running_pipelines:
                self.logger.info(f"Pipeline execution BLOCKED for project {project_id} - already running")
            else:
                self.logger.info(f"Pipeline execution BLOCKED for project {project_id} - capacity exceeded ({len(self.running_pipelines)}/{self.max_concurrent_pipelines})")
            return False
        
        # All checks passed - start pipeline
        self.logger.info(f"Starting code review pipeline for project {project_id} (chat_active={chat_status['is_active']}, pipelines={len(self.running_pipelines)}/{self.max_concurrent_pipelines})")
        self.running_pipelines.add(project_id)
        
        asyncio.create_task(
            self._execute_pipeline_with_cleanup(changes, project_id, app)
        )
        return True
    
    async def _execute_pipeline_with_cleanup(self, changes: List[FileChange], project_id: int, app) -> None:
        """Execute pipeline and ensure cleanup happens regardless of outcome.
        
        Args:
            changes: List of file changes to process
            project_id: ID of the project
            app: UI application instance for notifications
        """
        try:
            self.logger.info(f"Code review pipeline started for project {project_id}")
            pipeline_response = await code_review_pipeline(changes, project_id)
            
            if pipeline_response:
                self.logger.info(f"Code review pipeline completed successfully for project {project_id}")
                # Notify the user based on their preferences
                await notify_user(pipeline_response, project_id, app)
            else:
                self.logger.info(f"Code review pipeline completed - no issues found for project {project_id}")
                
        except Exception as e:
            self.logger.error(f"Code review pipeline error for project {project_id}: {str(e)}")
        finally:
            # Always remove from running set when pipeline is done
            self.running_pipelines.discard(project_id)
            self.logger.debug(f"Pipeline cleanup completed for project {project_id}")
    
    async def wait_for_completion(self, timeout_seconds: Optional[float] = None) -> bool:
        """Wait for all running pipelines to complete.
        
        Args:
            timeout_seconds: Maximum time to wait, None for no timeout
            
        Returns:
            True if all pipelines completed, False if timeout occurred
        """
        if not self.running_pipelines:
            return True
            
        self.logger.info(f"Waiting for {len(self.running_pipelines)} pipeline(s) to complete...")
        
        start_time = asyncio.get_event_loop().time()
        
        while self.running_pipelines:
            if timeout_seconds is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout_seconds:
                    self.logger.warning(f"Timeout waiting for pipelines to complete. {len(self.running_pipelines)} still running.")
                    return False
            
            await asyncio.sleep(0.1)  # Small delay to avoid busy waiting
        
        self.logger.info("All pipelines completed")
        return True
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status information.
        
        Returns:
            Dictionary with pipeline status details
        """
        chat_status = self.chat_state_service.get_chat_status()
        return {
            "running_count": len(self.running_pipelines),
            "max_concurrent": self.max_concurrent_pipelines,
            "running_project_ids": list(self.running_pipelines),
            "capacity_available": len(self.running_pipelines) < self.max_concurrent_pipelines,
            "chat_active": chat_status["is_active"],
            "active_chat_notification_id": chat_status["active_notification_id"],
            "can_start_new_pipeline": len(self.running_pipelines) < self.max_concurrent_pipelines and not chat_status["is_active"]
        } 
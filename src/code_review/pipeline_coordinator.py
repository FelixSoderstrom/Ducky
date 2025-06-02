import asyncio
import logging
from typing import Dict, Any, Optional, List, Set

from src.watcher.compare_versions import FileChange
from src.code_review.utils.pipeline import code_review_pipeline
from src.notifications import notify_user

logger = logging.getLogger("ducky.code_review.pipeline_coordinator")


class PipelineCoordinator:
    """Coordinates code review pipeline execution with concurrency control."""
    
    def __init__(self, max_concurrent_pipelines: int = 1):
        self.max_concurrent_pipelines = max_concurrent_pipelines
        self.running_pipelines: Set[int] = set()  # Track running pipeline IDs
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
            True if pipeline can start, False if at capacity or already running for this project
        """
        # Don't start if this project already has a running pipeline
        if project_id in self.running_pipelines:
            return False
            
        # Don't start if we're at max capacity
        if len(self.running_pipelines) >= self.max_concurrent_pipelines:
            return False
            
        return True
    
    async def execute_if_available(self, changes: List[FileChange], project_id: int, app) -> bool:
        """Execute pipeline if capacity is available.
        
        Args:
            changes: List of file changes to process
            project_id: ID of the project
            app: UI application instance for notifications
            
        Returns:
            True if pipeline was started, False if skipped due to capacity
        """
        if not self.can_start_pipeline(project_id):
            if project_id in self.running_pipelines:
                self.logger.info(f"Pipeline already running for project {project_id} - skipping")
            else:
                self.logger.info(f"Pipeline capacity exceeded ({len(self.running_pipelines)}/{self.max_concurrent_pipelines}) - skipping")
            return False
        
        # Start pipeline asynchronously
        self.logger.info(f"Starting code review pipeline for project {project_id}")
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
        return {
            "running_count": len(self.running_pipelines),
            "max_concurrent": self.max_concurrent_pipelines,
            "running_project_ids": list(self.running_pipelines),
            "capacity_available": len(self.running_pipelines) < self.max_concurrent_pipelines
        } 
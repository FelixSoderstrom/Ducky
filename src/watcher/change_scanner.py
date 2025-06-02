import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.config.app_config import AppConfig
from src.database.session import get_db
from src.database.models.projects import Project
from src.watcher.compare_versions import get_changes, FileChange
from src.watcher.project_manager import update_database_with_changes
from src.code_review.pipeline_coordinator import PipelineCoordinator

logger = logging.getLogger("ducky.watcher.change_scanner")


class ChangeScanner:
    """Handles continuous monitoring of project files for changes."""
    
    def __init__(self, config: AppConfig, pipeline_coordinator: PipelineCoordinator):
        self.config = config
        self.pipeline_coordinator = pipeline_coordinator
        self.logger = logger
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self, root_path: str, project_id: int, app) -> None:
        """Start continuous monitoring of the project directory.
        
        Args:
            root_path: Path to the project directory
            project_id: ID of the project in the database
            app: The UI application instance to check running state
        """
        if self._running:
            self.logger.warning("Scanner is already running")
            return
            
        self._running = True
        self.logger.info(f"Starting change monitoring for project {project_id} at {root_path}")
        
        # Start the scanning loop
        self._scan_task = asyncio.create_task(
            self._scan_loop(root_path, project_id, app)
        )
        
        try:
            await self._scan_task
        except asyncio.CancelledError:
            self.logger.info("Change monitoring cancelled")
        finally:
            self._running = False
    
    def stop_monitoring(self) -> None:
        """Stop the change monitoring process."""
        if not self._running:
            return
            
        self.logger.info("Stopping change monitoring...")
        self._running = False
        
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
    
    async def _scan_loop(self, root_path: str, project_id: int, app) -> None:
        """Main scanning loop that runs continuously.
        
        Args:
            root_path: Path to the project directory
            project_id: ID of the project in the database
            app: The UI application instance to check running state
        """
        last_scan_timestamp = None  # Track when we last scanned
        
        while self._running and app.running:
            try:
                current_scan_time = datetime.now()
                
                # Perform a single scan
                changes = await self._scan_once(root_path, project_id, last_scan_timestamp)
                
                if changes:
                    self.logger.info(f"Found {len(changes)} changes.")
                    
                    # Always update database with changes first
                    try:
                        update_database_with_changes(changes)
                        self.logger.debug("Database updated with changes.")
                    except Exception as e:
                        self.logger.error(f"Failed to update database: {str(e)}")
                    
                    # Try to start pipeline if capacity allows
                    pipeline_started = await self.pipeline_coordinator.execute_if_available(
                        changes, project_id, app
                    )
                    
                    if not pipeline_started:
                        self.logger.info("Changes saved to database but pipeline execution skipped.")
                else:
                    self.logger.debug("No changes detected.")
                
                # Update last scan timestamp after successful scan
                last_scan_timestamp = current_scan_time
                
            except Exception as e:
                self.logger.error(f"Error during scan: {str(e)}")
                if not app.running:
                    break
            
            # Sleep for configured interval before next scan
            try:
                await asyncio.sleep(self.config.scan_interval_seconds)
            except asyncio.CancelledError:
                break
    
    async def _scan_once(self, root_path: str, project_id: int, last_scan_timestamp: Optional[datetime]) -> List[FileChange]:
        """Perform a single scan for changes.
        
        Args:
            root_path: Path to the project directory
            project_id: ID of the project in the database
            last_scan_timestamp: Timestamp of the last scan (None for initial scan)
            
        Returns:
            List of FileChange objects representing detected changes
        """
        with get_db() as session:
            # Get fresh project instance with files eagerly loaded using 2.0 style
            stmt = (
                select(Project)
                .options(joinedload(Project.files))
                .where(Project.path == root_path)
            )
            result = session.execute(stmt).unique()
            project = result.scalar_one_or_none()
            
            if not project:
                self.logger.error("Project no longer exists in database.")
                raise RuntimeError("Project not found in database")
                
            # Get changes between database and local versions using timestamp comparison
            changes = get_changes(project, root_path, last_scan_timestamp)
            return changes
    
    def is_running(self) -> bool:
        """Check if the scanner is currently running.
        
        Returns:
            True if scanner is running, False otherwise
        """
        return self._running
    
    async def scan_now(self, root_path: str, project_id: int) -> List[FileChange]:
        """Perform an immediate one-time scan without starting continuous monitoring.
        
        Args:
            root_path: Path to the project directory
            project_id: ID of the project in the database
            
        Returns:
            List of FileChange objects representing detected changes
        """
        self.logger.info(f"Performing immediate scan for project {project_id}")
        return await self._scan_once(root_path, project_id, None) 
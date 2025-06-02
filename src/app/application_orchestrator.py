import asyncio
import logging
from typing import Optional

from src.config.app_config import AppConfig
from src.database.init_db import init_db
from src.ui.start_ui import start_ui
from src.app.project_initializer import ProjectInitializer
from src.watcher.project_manager import check_existing_project
from src.watcher.change_scanner import ChangeScanner
from src.code_review.pipeline_coordinator import PipelineCoordinator

logger = logging.getLogger("ducky.app.application_orchestrator")


class ApplicationOrchestrator:
    """Main application coordinator that manages the entire Ducky lifecycle."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.default()
        self.app = None
        self.project = None
        self.project_initializer = ProjectInitializer()
        self.pipeline_coordinator = PipelineCoordinator(
            max_concurrent_pipelines=self.config.max_concurrent_pipelines
        )
        self.change_scanner = ChangeScanner(self.config, self.pipeline_coordinator)
        self.logger = logger
        
    async def initialize(self) -> bool:
        """Initialize the application and its dependencies.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize database
            init_db()
            self.logger.info("Database initialized")
            
            # Start UI
            self.app = await start_ui()
            self.logger.info("UI started")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {str(e)}")
            return False
    
    async def setup_project(self) -> bool:
        """Set up project (either existing or new) and prepare for monitoring.
        
        Returns:
            True if project setup successful, False otherwise
        """
        # Get project directory from user
        root_path = await self.project_initializer.get_project_directory()
        if not root_path:
            self.logger.warning("No directory selected. Exiting...")
            return False
        
        # Check if project exists and handle accordingly
        existing_project = check_existing_project(root_path)
        
        if existing_project:
            # Handle existing project
            success = await self.project_initializer.handle_existing_project(existing_project, root_path)
            if not success:
                return False
                
            self.project = existing_project
            self.app.set_current_project_path(root_path)
            self.logger.info(f"Existing project '{existing_project.name}' ready for monitoring")
            
        else:
            # Handle new project initialization
            preferences = await self.project_initializer.collect_user_preferences(self.app)
            if not preferences:
                return False
            
            project = await self.project_initializer.setup_new_project(root_path, preferences)
            if not project:
                return False
                
            self.project = project
            self.app.set_current_project_path(root_path)
            self.logger.info(f"New project '{project.name}' ready for monitoring")
        
        return True
    
    async def run(self) -> None:
        """Run the main application loop.
        
        This coordinates the UI and file monitoring systems.
        """
        if not self.project:
            raise RuntimeError("Project must be set up before running")
        
        try:
            # Start both UI updates and change monitoring concurrently
            await asyncio.gather(
                self.change_scanner.start_monitoring(
                    self.project.path, 
                    self.project.id, 
                    self.app
                ),
                self.app.update()
            )
        except asyncio.CancelledError:
            self.logger.info("Application run loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in main run loop: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the application and cleanup resources."""
        self.logger.info("Shutting down application...")
        
        try:
            # Stop change monitoring
            if self.change_scanner.is_running():
                self.change_scanner.stop_monitoring()
                self.logger.debug("Change scanner stopped")
            
            # Wait for any running pipelines to complete (with timeout)
            completed = await self.pipeline_coordinator.wait_for_completion(timeout_seconds=10.0)
            if not completed:
                self.logger.warning("Some pipelines did not complete within timeout")
            
            # Close UI application
            if self.app and self.app.running:
                self.app.close_app()
                self.logger.debug("UI application closed")
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
        
        self.logger.info("Application shutdown complete")
    
    def get_status(self) -> dict:
        """Get current application status information.
        
        Returns:
            Dictionary containing application status details
        """
        return {
            "config": {
                "scan_interval": self.config.scan_interval_seconds,
                "max_pipelines": self.config.max_concurrent_pipelines,
                "log_level": self.config.log_level
            },
            "project": {
                "name": self.project.name if self.project else None,
                "path": self.project.path if self.project else None,
                "id": self.project.id if self.project else None
            },
            "scanner": {
                "running": self.change_scanner.is_running()
            },
            "pipelines": self.pipeline_coordinator.get_pipeline_status(),
            "ui": {
                "running": self.app.running if self.app else False
            }
        } 
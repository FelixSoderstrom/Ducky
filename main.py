import asyncio
import sys
import logging
from datetime import datetime

# Initialize logging first before other imports
from src.utils.logging_config import setup_logging
setup_logging(log_level="INFO")

from src.database.init_db import init_db
from src.ui.start_ui import start_ui
from src.ui.utils.user_interaction import get_dir_path
from src.ui.utils.notification_preferences import get_notification_preference
from src.watcher.project_manager import check_existing_project, handle_existing_project, initialize_new_project, update_database_with_changes
from src.database.session import get_db
from src.watcher.compare_versions import get_changes
from src.code_review.utils.pipeline import code_review_pipeline
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.database.models.projects import Project

# Create logger for main module
logger = logging.getLogger("ducky.main")

# Configurable scan interval in seconds (can be integrated into UI later)
# This interval balances responsiveness with system resource usage.
# Shorter intervals = more responsive but higher CPU usage
# Longer intervals = less CPU usage but slower change detection
SCAN_INTERVAL_SECONDS = 30

async def scan_for_changes(root_path: str, project_id: int, app) -> None:
    """Continuously scan for changes in the codebase using timestamp-based comparison.
    
    Args:
        root_path: Path to the project directory
        project_id: ID of the project in the database
        app: The UI application instance to check running state
    """
    last_scan_timestamp = None  # Track when we last scanned
    
    while app.running:
        try:
            current_scan_time = datetime.now()
            
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
                    logger.error("Project no longer exists in database. Exiting...")
                    app.close_app()
                    return
                    
                # Get changes between database and local versions using timestamp comparison
                changes = get_changes(project, root_path, last_scan_timestamp)
                
                if changes:
                    logger.info(f"Found {len(changes)} changes. Running code review...")
                    
                    # Ensure all changes have project_id set
                    for change in changes:
                        change['project_id'] = project_id
                    
                    try:
                        # Run the code review pipeline
                        code_review_pipeline(changes, project_id)
                        logger.info("Code review pipeline completed.")
                    except Exception as e:
                        logger.error(f"Code review pipeline error: {str(e)}")
                        logger.info("Pipeline completed with error, proceeding to update database.")
                    finally:
                        # Always update database after pipeline runs (success or failure)
                        # This ensures the database stays in sync with the filesystem
                        update_database_with_changes(changes)
                else:
                    logger.debug("No changes detected.")
                
                # Update last scan timestamp after successful scan
                last_scan_timestamp = current_scan_time
                
        except Exception as e:
            logger.error(f"Error during scan: {str(e)}")
            if not app.running:
                return
            
        # Sleep for configured interval before next scan
        try:
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return


async def main():
    """Main entry point running UI and codebase operations concurrently."""
    # Initialize the database first
    init_db()
    
    # Start the UI
    app = await start_ui()
    
    # Get directory path from user
    root_path = get_dir_path()
    if not root_path:
        logger.warning("No directory selected. Exiting...")
        app.close_app()
        return
    
    # Check if project exists and handle accordingly
    existing_project = check_existing_project(root_path)
    if existing_project:
        await handle_existing_project(existing_project, root_path)
        # Start scanning loop for existing project
        try:
            await asyncio.gather(
                scan_for_changes(root_path, existing_project.id, app),
                app.update()
            )
        except asyncio.CancelledError:
            logger.info("Shutting down gracefully...")
        finally:
            if app.running:
                app.close_app()
        return

    # Handle new project initialization
    api_key = await app.get_api_key()
    if not api_key:
        logger.warning("No API key provided. Exiting...")
        app.close_app()
        return
    
    notification_pref = await get_notification_preference(app.root)
    if not notification_pref:
        logger.warning("No notification preference selected. Exiting...")
        app.close_app()
        return
    
    try:
        await initialize_new_project(root_path, api_key, notification_pref)
        project = check_existing_project(root_path)
        if not project:
            logger.error("Failed to initialize project. Exiting...")
            app.close_app()
            return
            
        # Start scanning loop for new project
        try:
            await asyncio.gather(
                scan_for_changes(root_path, project.id, app),
                app.update()
            )
        except asyncio.CancelledError:
            logger.info("Shutting down gracefully...")
        finally:
            if app.running:
                app.close_app()
                
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        app.close_app()


if __name__ == "__main__":
    asyncio.run(main())

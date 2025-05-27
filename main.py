import asyncio
import sys
from src.database.init_db import init_db
from src.ui.start_ui import start_ui
from src.ui.utils.user_interaction import get_dir_path
from src.ui.utils.notification_preferences import get_notification_preference
from src.watcher.project_manager import check_existing_project, handle_existing_project, initialize_new_project
from src.database.session import get_db
from src.watcher.compare_versions import get_changes
from src.code_review.utils.pipeline import code_review_pipeline
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.database.models.projects import Project


async def scan_for_changes(root_path: str, project_id: int, app) -> None:
    """Continuously scan for changes in the codebase.
    
    Args:
        root_path: Path to the project directory
        project_id: ID of the project in the database
        app: The UI application instance to check running state
    """
    while app.running:
        try:
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
                    print("Project no longer exists in database. Exiting...")
                    app.close_app()
                    return
                    
                # Get changes between database and local versions
                changes = get_changes(project, root_path)
                
                if changes:
                    print(f"Found {len(changes)} changes. Running code review...")
                    code_review_pipeline(changes)
                    
                    # Update database with new changes
                    for change in changes:
                        change['project_id'] = project_id
                    await handle_existing_project(project, root_path)
                
        except Exception as e:
            print(f"Error during scan: {str(e)}")
            if not app.running:
                return
            
        # Sleep for 10 seconds before next scan
        try:
            await asyncio.sleep(10)
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
        print("No directory selected. Exiting...")
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
            print("\nShutting down gracefully...")
        finally:
            if app.running:
                app.close_app()
        return
        
    # Handle new project initialization
    api_key = await app.get_api_key()
    if not api_key:
        print("No API key provided. Exiting...")
        app.close_app()
        return
    
    notification_pref = await get_notification_preference(app.root)
    if not notification_pref:
        print("No notification preference selected. Exiting...")
        app.close_app()
        return
    
    try:
        await initialize_new_project(root_path, api_key, notification_pref)
        project = check_existing_project(root_path)
        if not project:
            print("Failed to initialize project. Exiting...")
            app.close_app()
            return
            
        # Start scanning loop for new project
        try:
            await asyncio.gather(
                scan_for_changes(root_path, project.id, app),
                app.update()
            )
        except asyncio.CancelledError:
            print("\nShutting down gracefully...")
        finally:
            if app.running:
                app.close_app()
                
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        app.close_app()


if __name__ == "__main__":
    asyncio.run(main())

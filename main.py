import asyncio
import sys
from typing import List
from src.database.init_db import init_db
from src.database.operations.post_project import post_project
from src.database.operations.get_project import get_project_by_path
from src.database.models.projects import Project
from src.database.session import get_db
from src.ui.start_ui import start_ui
from src.ui.utils.user_interaction import get_dir_path
from src.watcher.get_codebase import get_codebase
from src.watcher.compare_versions import get_changes, FileChange
from src.database.operations.post_changes import post_changes
from src.ui.utils.notification_preferences import NOTIFICATION_TYPE_MAP, NotificationPreference, get_notification_preference


async def run_codebase_operations(root_path: str, api_key: str, notification_pref: NotificationPreference):
    """Run initial codebase scan.
    
    Args:
        root_path: The directory path to scan
        api_key: The Anthropic API key to include in the codebase dict
        notification_pref: User's preferred notification method
    """
    codebase = get_codebase(root_path, api_key)
    # Add project path and notification preference to codebase dict
    codebase['project_path'] = root_path
    codebase['notification_preference'] = NOTIFICATION_TYPE_MAP[notification_pref]
    print("Initial codebase scan:")
    print(codebase)
    
    # Post to database
    try:
        with get_db() as session:
            post_project(session, codebase)
    except Exception as e:
        print(f"Failed to post project to database: {str(e)}")
        sys.exit(1)


async def handle_existing_project(project: Project, root_path: str):
    """Handle an existing project from the database.
    
    Args:
        project: The existing Project instance from the database
        root_path: Path to the local project directory
    """
    print(f"Project '{project.name}' already exists in database")
    
    # Get changes between database and local versions
    changes: List[FileChange] = get_changes(project, root_path)
    
    # Post changes to database
    with get_db() as session:
        post_changes(session, changes)
    
    print(f"Found {len(changes)} changed files")


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
        sys.exit(0)
    
    # Check if project already exists
    try:
        with get_db() as session:
            existing_project = get_project_by_path(session, root_path)
            if existing_project:
                await handle_existing_project(existing_project, root_path)
                return
    except Exception as e:
        print(f"Error checking for existing project: {str(e)}")
        sys.exit(1)
    
    # Get Anthropic API key for new project
    api_key = await app.get_api_key()
    if not api_key:
        print("No API key provided. Exiting...")
        sys.exit(0)
    
    # Get notification preference using the standalone function
    notification_pref = await get_notification_preference(app.root)
    if not notification_pref:
        print("No notification preference selected. Exiting...")
        sys.exit(0)
    
    # Run the codebase scan for new project
    try:
        await run_codebase_operations(root_path, api_key, notification_pref)
        # Continue running the UI after scan
        await app.update()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

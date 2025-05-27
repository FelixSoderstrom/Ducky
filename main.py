import asyncio
import sys
from src.database.init_db import init_db
from src.ui.start_ui import start_ui
from src.ui.utils.user_interaction import get_dir_path
from src.ui.utils.notification_preferences import get_notification_preference
from src.watcher.project_manager import check_existing_project, handle_existing_project, initialize_new_project


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
    
    # Check if project exists and handle accordingly
    existing_project = check_existing_project(root_path)
    if existing_project:
        await handle_existing_project(existing_project, root_path)
        await app.update()
        return
        
    # Handle new project initialization
    api_key = await app.get_api_key()
    if not api_key:
        print("No API key provided. Exiting...")
        sys.exit(0)
    
    notification_pref = await get_notification_preference(app.root)
    if not notification_pref:
        print("No notification preference selected. Exiting...")
        sys.exit(0)
    
    try:
        await initialize_new_project(root_path, api_key, notification_pref)
        await app.update()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

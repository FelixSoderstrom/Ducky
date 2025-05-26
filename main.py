import asyncio
import sys
from src.database.init_db import init_db
from src.ui.start_ui import start_ui
from src.ui.utils.user_interaction import get_dir_path
from src.watcher.get_codebase import get_codebase


async def run_codebase_operations(root_path: str):
    """Run initial codebase scan.
    
    Args:
        root_path: The directory path to scan.
    """
    codebase = get_codebase(root_path)
    print("Initial codebase scan:")
    print(codebase)


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
    
    # Run the codebase scan
    try:
        await run_codebase_operations(root_path)
        # Continue running the UI after scan
        await app.update()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

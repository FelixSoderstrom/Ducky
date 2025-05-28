from typing import Optional
from src.database.models.projects import Project
from src.database.operations.get_project import get_project_by_path
from src.database.operations.post_project import post_project
from src.database.operations.post_changes import post_changes
from src.database.session import get_db
from src.watcher.get_codebase import get_codebase
from src.watcher.compare_versions import get_changes, FileChange
from src.ui.utils.notification_preferences import NotificationPreference, NOTIFICATION_TYPE_MAP
import sys
from typing import List
from sqlalchemy.orm import Session
import sqlalchemy.orm


def check_existing_project(root_path: str) -> Optional[Project]:
    """Check if a project already exists in the database.
    
    Args:
        root_path: Path to the project directory
        
    Returns:
        Project if it exists, None otherwise
        
    Raises:
        Exception: If there's an error accessing the database
    """
    try:
        with get_db() as session:
            return get_project_by_path(session, root_path)
    except Exception as e:
        print(f"Error checking for existing project: {str(e)}")
        sys.exit(1)


def get_project_with_files(session: Session, project_id: int) -> Project:
    """Get a project with its files eagerly loaded.
    
    Args:
        session: SQLAlchemy session
        project_id: ID of the project to fetch
        
    Returns:
        Project instance with files relationship loaded
    """
    # Query the project with files relationship eagerly loaded
    return session.query(Project).options(
        sqlalchemy.orm.joinedload(Project.files)
    ).get(project_id)


async def handle_existing_project(project: Project, root_path: str) -> None:
    """Handle operations for an existing project.
    
    Args:
        project: The existing Project instance from the database
        root_path: Path to the local project directory
    """
    print(f"Project '{project.name}' already exists in database")
    print("Existing project detected - the scanning loop will detect and process any new changes.")
    
    # For existing projects, we don't need to do a full sync here since the 
    # regular scanning loop will handle detecting and processing changes efficiently.
    # This prevents the performance issue of processing thousands of files on startup.
    
    print("Ready to monitor for changes...")


def update_database_with_changes(changes: List[FileChange]) -> None:
    """Update the database with pre-detected changes.
    
    Args:
        changes: List of FileChange objects to update in the database
    """
    if not changes:
        print("No changes to update in database")
        return
        
    try:
        with get_db() as session:
            post_changes(session, changes)
        print(f"Successfully updated database with {len(changes)} changes")
    except Exception as e:
        print(f"Error updating database with changes: {str(e)}")
        raise


async def initialize_new_project(root_path: str, api_key: str, notification_pref: NotificationPreference) -> None:
    """Initialize a new project in the database.
    
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
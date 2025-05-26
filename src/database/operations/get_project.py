from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.models.projects import Project
from src.database.utils.path_utils import normalize_path

def get_project_by_path(session: Session, project_path: str) -> Optional[Project]:
    """Check if a project exists in the database by its path.
    
    Args:
        session: SQLAlchemy session instance
        project_path: The full path of the project directory
        
    Returns:
        Project if found, None otherwise
    """
    try:
        # Normalize the input path
        normalized_path = normalize_path(project_path)
        
        # Query for project with matching normalized path using 2.0 style
        stmt = select(Project).where(Project.path == normalized_path)
        result = session.execute(stmt)
        project = result.scalar_one_or_none()
        
        return project
    
    except Exception as e:
        print(f"Error querying database: {str(e)}")
        raise 
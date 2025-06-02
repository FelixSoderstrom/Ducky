from datetime import datetime
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.models.files import File
from src.watcher.compare_versions import FileChange

# Create logger for this module
logger = logging.getLogger("ducky.database.operations.post_changes")

def post_changes(session: Session, changes: List[FileChange]) -> None:
    """Update the database with file changes from the local codebase.
    
    Args:
        session: SQLAlchemy session instance
        changes: List of FileChange objects containing file differences
    """
    try:
        for change in changes:
            if change['new_version'] == '':
                # File was deleted locally, remove from database
                stmt = select(File).where(File.path == change['path'])
                file = session.execute(stmt).scalar_one_or_none()
                if file:
                    session.delete(file)
            else:
                # File is new or modified
                stmt = select(File).where(File.path == change['path'])
                file = session.execute(stmt).scalar_one_or_none()
                
                if file:
                    # Update existing file
                    file.content = change['new_version']
                    file.last_edit = datetime.fromisoformat(change['last_edit'])
                else:
                    # Create new file with project_id from change
                    file = File(
                        project_id=change['project_id'],
                        path=change['path'],
                        name=change['filename'],
                        is_dir=change['is_dir'],
                        content=change['new_version'],
                        last_edit=datetime.fromisoformat(change['last_edit'])
                    )
                    session.add(file)
        
        # Commit all changes
        session.commit()
        logger.info("Successfully updated database with file changes")
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating database with changes: {str(e)}")
        raise
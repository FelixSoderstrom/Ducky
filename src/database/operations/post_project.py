from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.models.projects import Project
from src.database.models.files import File
from src.database.models.configs import Config
from src.database.models.notification_types import NotificationType
from src.database.utils.path_utils import normalize_path

def post_project(session: Session, codebase: Dict[str, Any]) -> None:
    """Post initial project scan to database.
    
    Args:
        session: SQLAlchemy session instance
        codebase: Dictionary containing project and file information with structure:
            {
                project_name: str,
                api_key: str,
                project_path: str,
                notification_preference: str,  # One of: 'Voice', 'Text', 'Badge'
                files: [
                    {
                        filename: str,
                        last_edit: timestamp,
                        file_contents: str,
                        full_path: str,
                        is_dir: bool
                    },
                    ...
                ]
            }
    """
    try:
        # Create project
        project = Project(
            name=codebase['project_name'],
            api_key=codebase['api_key'],
            path=normalize_path(codebase['project_path'])
        )
        session.add(project)
        session.flush()  # Get project ID
        
        # Get notification type ID and create config
        stmt = select(NotificationType.id).where(
            NotificationType.name == codebase['notification_preference']
        )
        notification_type_id = session.execute(stmt).scalar_one()
        
        # Create config linking project to notification type
        config = Config(
            project_id=project.id,
            notification_id=notification_type_id
        )
        session.add(config)
        
        # Add files
        for file_data in codebase['files']:
            normalized_file_path = normalize_path(file_data['full_path'])
            
            file = File(
                project_id=project.id,
                path=normalized_file_path,
                name=file_data['filename'],
                is_dir=file_data['is_dir'],
                content=file_data['file_contents'],
                last_edit=datetime.fromisoformat(file_data['last_edit'])
            )
            session.add(file)
        
        session.commit()
        print(f"Successfully added project {project.name} to database")
        
    except IntegrityError as e:
        session.rollback()
        print(f"Error: Project with API key {codebase['api_key']} already exists")
        raise
    except Exception as e:
        session.rollback()
        print(f"Error adding project to database: {str(e)}")
        raise 
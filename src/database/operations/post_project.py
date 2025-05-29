from datetime import datetime
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.models.projects import Project
from src.database.models.files import File
from src.database.models.configs import Config
from src.database.models.notification_types import NotificationType
from src.database.utils.path_utils import normalize_path
from src.database.session import get_db

# Create logger for this module
logger = logging.getLogger("ducky.database.operations.post_project")

def post_project(session: Session, codebase: Dict[str, Any]) -> None:
    """Post initial project scan to database.
    
    Args:
        session: SQLAlchemy session instance
        codebase: Dictionary containing project and file information with structure:
            {
                project_name: str,
                anthropic_key: str,
                eleven_labs_key: str (optional),
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
            anthropic_key=codebase['anthropic_key'],
            eleven_labs_key=codebase.get('eleven_labs_key'),
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
        logger.info(f"Successfully added project {project.name} to database")
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Error: Project with Anthropic API key {codebase['anthropic_key']} already exists")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding project to database: {str(e)}")
        raise

def save_project_to_db(
    codebase: Dict[str, Any], 
    anthropic_key: str,
    eleven_labs_key: Optional[str] = None
) -> None:
    """Save a project and its files to the database.
    
    Args:
        codebase: Dictionary containing project metadata and files
        anthropic_key: The Anthropic API key
        eleven_labs_key: The ElevenLabs API key (optional)
    """
    try:
        with get_db() as session:
            # Check if project already exists by path
            stmt = select(Project).where(Project.path == normalize_path(codebase['project_path']))
            existing_project = session.execute(stmt).scalar_one_or_none()
            if existing_project:
                logger.warning(f"Project already exists: {codebase['name']}")
                return
            
            # Create new project
            project = Project(
                name=codebase['name'],
                anthropic_key=anthropic_key,
                eleven_labs_key=eleven_labs_key,
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
            logger.info(f"Successfully added project {project.name} to database")
            
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Error: Project with Anthropic API key {anthropic_key} already exists")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding project to database: {str(e)}")
        raise 
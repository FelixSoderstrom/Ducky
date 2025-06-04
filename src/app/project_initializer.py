import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from src.database.models.projects import Project
from src.ui.utils.user_interaction import get_dir_path
from src.ui.utils.notification_preferences import get_notification_preference, NotificationPreference
from src.watcher.project_manager import check_existing_project, handle_existing_project, initialize_new_project

logger = logging.getLogger("ducky.app.project_initializer")


@dataclass
class ProjectPreferences:
    """Container for user project preferences."""
    api_key: str
    notification_pref: NotificationPreference


class ProjectInitializer:
    """Handles project initialization and setup flow."""
    
    def __init__(self):
        self.logger = logger
    
    async def setup_project(self, app) -> Optional[Project]:
        """Main entry point for project setup flow.
        
        Args:
            app: UI application instance
            
        Returns:
            Project instance if successful, None if cancelled/failed
        """
        # Get project directory
        root_path = get_dir_path()
        if not root_path:
            self.logger.warning("No directory selected.")
            return None
        
        # Set project path in app for settings access
        app.set_current_project_path(root_path)
        
        # Check if project already exists
        existing_project = check_existing_project(root_path)
        if existing_project:
            # Handle existing project - pass correct parameters and handle return value
            await handle_existing_project(existing_project, root_path)
            self.logger.info(f"Using existing project: {existing_project.name}")
            return existing_project
        
        # Get user preferences for new project
        preferences = await self.collect_user_preferences(app)
        if not preferences:
            return None
        
        # Initialize new project
        return await self.setup_new_project(root_path, preferences)
    
    async def collect_user_preferences(self, app) -> Optional[ProjectPreferences]:
        """Collect API key and notification preferences from user.
        
        Args:
            app: UI application instance
            
        Returns:
            ProjectPreferences if successful, None if cancelled
        """
        # Get API key
        api_key = await app.get_api_key()
        if not api_key:
            self.logger.warning("No API key provided.")
            return None
        
        # Get notification preferences
        notification_pref = await get_notification_preference(app.root)
        if not notification_pref:
            self.logger.warning("No notification preference selected.")
            return None
        
        return ProjectPreferences(
            api_key=api_key,
            notification_pref=notification_pref
        )
    
    async def setup_new_project(self, root_path: str, preferences: ProjectPreferences) -> Optional[Project]:
        """Initialize a new project with the given preferences.
        
        Args:
            root_path: Path to the project directory
            preferences: User preferences for the project
            
        Returns:
            Project instance if successful, None otherwise
        """
        await initialize_new_project(
            root_path=root_path,
            anthropic_key=preferences.api_key,
            notification_pref=preferences.notification_pref
        )
        
        # Verify project was created
        project = check_existing_project(root_path)
        if not project:
            self.logger.error("Failed to initialize project - not found in database")
            return None
            
        self.logger.info(f"New project '{project.name}' initialized successfully")
        return project 
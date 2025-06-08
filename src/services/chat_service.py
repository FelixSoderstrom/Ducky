"""Chat service for managing conversational code review discussions."""

import logging
import asyncio
import os
from typing import Dict, Any, Optional

from ..code_review.agents.base.agent_factory import AgentFactory
from ..code_review.agents.rubberduck import RubberDuck
from ..ui.components.chat_window import ChatWindow
from ..database.session import get_db
from ..database.models.projects import Project

logger = logging.getLogger("ducky.services.chat_service")


class ChatService:
    """Business logic for chat lifecycle management."""
    
    def __init__(self, ui_app):
        """
        Initialize the chat service.
        
        Args:
            ui_app: The DuckyUI application instance
        """
        self.ui_app = ui_app
        self.rubberduck_agent: Optional[RubberDuck] = None
        self.chat_window: Optional[ChatWindow] = None
        self.notification_id: Optional[str] = None
        self._chat_active = False
        
    async def start_chat(self, pipeline_data: Dict[str, Any], notification_id: str) -> bool:
        """
        Start a chat session with the RubberDuck agent.
        
        Args:
            pipeline_data: Dictionary containing notification, warning, solution, etc.
            notification_id: ID of the notification that triggered the chat
            
        Returns:
            True if chat started successfully, False otherwise
        """
        try:
            logger.info("Starting chat session")
            self.notification_id = notification_id
            
            # Initialize RubberDuck agent
            if not await self._initialize_rubberduck(pipeline_data):
                return False
            
            # Create and show chat window
            self._create_chat_window()
            
            # Add initial greeting from Ducky
            await self._send_initial_greeting()
            
            self._chat_active = True
            logger.info("Chat session started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start chat session: {str(e)}")
            self._cleanup_resources()
            return False
    
    async def send_message(self, user_message: str) -> None:
        """
        Send a user message to Ducky and display the response.
        
        Args:
            user_message: Message from the user
        """
        if not self._chat_active or not self.rubberduck_agent or not self.chat_window:
            logger.warning("Attempted to send message when chat not active")
            return
        
        try:
            # Show typing indicator (direct UI update since we're on main thread)
            if self.chat_window:
                self.chat_window.show_typing_indicator()
            
            logger.info(f"Processing user message: {user_message[:50]}...")
            
            # Get response from RubberDuck agent (this is the async part)
            logger.info("Calling RubberDuck agent...")
            response = await self.rubberduck_agent.chat(user_message)
            logger.info(f"RubberDuck response received: {response[:50]}...")
            
            # Hide typing indicator and add Ducky's response (direct UI updates)
            if self.chat_window:
                self.chat_window.hide_typing_indicator()
                self.chat_window.add_message('ducky', response)
            
            logger.info("Message processing completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Hide typing indicator and show error message (direct UI updates)
            if self.chat_window:
                self.chat_window.hide_typing_indicator()
                self.chat_window.add_message(
                    'ducky', 
                    "I'm having trouble processing your message right now. Could you try again?"
                )
    
    def close_chat(self) -> None:
        """Close the chat session and cleanup resources."""
        try:
            logger.info("Closing chat session")
            
            # Remove notification from badge (as per requirement)
            if self.notification_id:
                self.ui_app.remove_unhandled_notification(self.notification_id)
                logger.info(f"Removed notification {self.notification_id} from badge")
            
            self._cleanup_resources()
            logger.info("Chat session closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing chat session: {str(e)}")
    
    async def _initialize_rubberduck(self, pipeline_data: Dict[str, Any]) -> bool:
        """Initialize the RubberDuck agent with pipeline data."""
        try:
            # Get API key from database or environment
            api_key = self._get_api_key()
            if not api_key:
                logger.error("No Anthropic API key available")
                return False
            
            # Create RubberDuck agent using factory
            self.rubberduck_agent = AgentFactory.create_rubberduck(api_key)
            
            # Initialize conversation with pipeline data
            self.rubberduck_agent.initialize_conversation(pipeline_data)
            
            logger.info("RubberDuck agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RubberDuck agent: {str(e)}")
            return False
    
    def _create_chat_window(self) -> None:
        """Create and configure the chat window."""
        self.chat_window = ChatWindow(
            parent_root=self.ui_app.root,
            on_message_send=self._on_message_send,
            on_close=self._on_chat_close
        )
        self.chat_window.show()
        logger.info("Chat window created and displayed")
    
    async def _send_initial_greeting(self) -> None:
        """Send initial greeting message from Ducky."""
        greeting = ("Hi! I'm Ducky, your code review assistant. I see you want to discuss "
                   "the code review feedback. What would you like to know about it?")
        
        self.chat_window.add_message('ducky', greeting)
        logger.info("Initial greeting sent")
    
    def _get_api_key(self) -> Optional[str]:
        """Get Anthropic API key from database or environment."""
        try:
            # Try environment variable first as it's more reliable
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                logger.info("Using API key from environment variable")
                return api_key
            
            # Try to get from database as secondary option
            project_id = getattr(self.ui_app, 'current_project_id', 1)
            
            with get_db() as session:
                project = session.get(Project, project_id)
                if project and project.anthropic_key:
                    logger.info(f"Using API key from database for project {project_id}")
                    return project.anthropic_key
                else:
                    logger.info(f"No API key found in database for project {project_id}")
            
            logger.warning("No Anthropic API key found in environment or database")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving API key: {str(e)}")
            # Final fallback to environment variable
            return os.getenv('ANTHROPIC_API_KEY')
    
    def _cleanup_resources(self) -> None:
        """Clean up chat resources."""
        if self.chat_window:
            self.chat_window.hide()
            self.chat_window = None
        
        if self.rubberduck_agent:
            # Reset conversation to free memory
            self.rubberduck_agent.reset_conversation()
            self.rubberduck_agent = None
        
        self._chat_active = False
        self.notification_id = None
        logger.info("Chat resources cleaned up")
    
    def _on_message_send(self, message: str) -> None:
        """Handle message send from chat window (async task scheduling)."""
        logger.info(f"Message send triggered: {message[:50]}...")
        
        try:
            # Schedule async operation on the existing event loop (main thread)
            loop = asyncio.get_event_loop()
            loop.create_task(self.send_message(message))
            
        except Exception as e:
            logger.error(f"Error scheduling async message handler: {str(e)}")
            # Show error in UI (we're on main thread, so direct UI updates are safe)
            if self.chat_window:
                self.chat_window.hide_typing_indicator()
                self.chat_window.add_message(
                    'ducky', 
                    "I'm having trouble processing your message right now. Could you try again?"
                )
    
    def _on_chat_close(self) -> None:
        """Handle chat window close button."""
        self.close_chat() 
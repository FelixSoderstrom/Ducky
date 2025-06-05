"""RubberDuck agent for conversational code review discussions."""

from typing import Optional, List, Dict, Any
from anthropic import Anthropic

from .base.rag_agent import RAGCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext


class RubberDuck(RAGCapableAgent):
    """Conversational agent for discussing code review feedback with developers."""
    
    def __init__(self, api_key: str):
        super().__init__("RubberDuck", "rubberduck")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.conversation_history: List[Dict[str, str]] = []
        self.pipeline_data: Optional[Dict[str, Any]] = None
        
    def initialize_conversation(self, pipeline_data: Dict[str, Any]) -> None:
        """
        Initialize the conversation with pipeline data from code review.
        
        Args:
            pipeline_data: Dictionary containing notification, warning, solution, etc.
        """
        self.pipeline_data = pipeline_data
        self.conversation_history = []
        
        # Create initial context message for the conversation
        warning_message = pipeline_data.get("warning", "")
        notification_text = pipeline_data.get("notification", "")
        solution = pipeline_data.get("solution", "")
        
        initial_context = f"""
Code Review Context:
- Warning: {warning_message}
- Notification: {notification_text}
- Suggested Solution: {solution}

The developer has chosen to discuss this code review feedback.
"""
        
        self.logger.info("RubberDuck conversation initialized with pipeline data")
        self.cr_logger.info(f"[{self.name}] Conversation initialized")
        self.cr_logger.info(f"[{self.name}] Warning: {warning_message[:100]}...")
        
    async def chat(self, user_message: str) -> str:
        """
        Process a chat message from the user and return Ducky's response.
        
        Args:
            user_message: Message from the developer
            
        Returns:
            Ducky's response
        """
        if not self.pipeline_data:
            return "I need to be initialized with pipeline data before we can chat."
        
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            self.logger.info(f"Processing chat message: {user_message[:50]}...")
            self.cr_logger.info(f"[{self.name}] User: {user_message}")
            
            # Build messages for API call
            messages = self._build_conversation_messages()
            
            # Call Claude API (synchronous)
            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=messages,
                max_tokens=1000
            )
            
            ducky_response = response.content[0].text
            
            # Add Ducky's response to conversation history
            self.conversation_history.append({
                "role": "assistant", 
                "content": ducky_response
            })
            
            self.logger.info(f"Generated response: {ducky_response[:50]}...")
            self.cr_logger.info(f"[{self.name}] Ducky: {ducky_response}")
            
            return ducky_response
            
        except Exception as e:
            self.logger.error(f"Chat processing failed: {str(e)}")
            self.cr_logger.error(f"[{self.name}] Chat error: {str(e)}")
            return "I'm having trouble processing your message right now. Could you try again?"
    
    def _build_conversation_messages(self) -> List[Dict[str, str]]:
        """Build the messages array for the Anthropic API call."""
        messages = []
        
        # Add initial context if this is the first exchange
        if len(self.conversation_history) == 1:  # Only user's first message
            context_message = self._build_initial_context_message()
            messages.append({
                "role": "user",
                "content": context_message
            })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        return messages
    
    def _build_initial_context_message(self) -> str:
        """Build the initial context message with pipeline data."""
        warning_message = self.pipeline_data.get("warning", "No warning provided")
        notification_text = self.pipeline_data.get("notification", "No notification provided")
        solution = self.pipeline_data.get("solution", "No solution provided")
        
        return f"""I'm connecting you with a developer who received a code review notification and wants to discuss it.

Here's the code review context:

Warning Details: {warning_message}

Notification Sent: {notification_text}

Suggested Solution: {solution}

The developer's first message: {self.conversation_history[0]['content']}

Please help them understand the issue and how to fix it."""
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation state."""
        return {
            "message_count": len(self.conversation_history),
            "pipeline_data_available": self.pipeline_data is not None,
            "last_user_message": self.conversation_history[-2]['content'] if len(self.conversation_history) >= 2 else None,
            "last_ducky_response": self.conversation_history[-1]['content'] if len(self.conversation_history) >= 1 and self.conversation_history[-1]['role'] == 'assistant' else None
        }
    
    def reset_conversation(self) -> None:
        """Reset the conversation history while keeping pipeline data."""
        self.conversation_history = []
        self.logger.info("Conversation history reset")
        self.cr_logger.info(f"[{self.name}] Conversation reset")
    
    # Required method from CodeReviewAgent (not used in chat mode)
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """Not used - RubberDuck operates in chat mode, not pipeline mode."""
        return PipelineResult.CONTINUE, context.current_warning
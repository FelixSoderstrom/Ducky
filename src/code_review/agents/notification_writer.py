# Summarizes the warning message into a more user friendly message

# Args: New file, old file, path to new file, warning message(from initial_assessment.py)

# Returns: User friendly warning message

from typing import Optional
import json
from anthropic import Anthropic

from ..utils.pipeline import CodeReviewAgent, PipelineResult, WarningMessage, AgentContext


class NotificationWriter(CodeReviewAgent):
    """Agent that writes user-friendly notification messages."""
    
    def __init__(self, api_key: str):
        super().__init__("NotificationWriter", "notification_writer")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, str]:
        """
        Write user-friendly notification message. Cannot cancel pipeline.
        Returns notification string instead of warning message.
        """
        self.logger.info("Writing notification message")
        
        if not context.current_warning:
            self.logger.warning("No warning message to convert to notification")
            return PipelineResult.CONTINUE, "Hey! I noticed some changes in your code that might need attention. Let's chat about it!"
        
        try:
            # Generate friendly notification using LLM
            notification = self._generate_friendly_notification(context.current_warning)
            return PipelineResult.CONTINUE, notification
            
        except Exception as e:
            self.logger.error(f"Notification writing failed: {str(e)}")
            # Fallback to basic notification
            return PipelineResult.CONTINUE, "Hey! I noticed something interesting in your recent code changes. Want to chat about it? I have some helpful insights to share!"
    
    def _generate_friendly_notification(self, warning: WarningMessage) -> str:
        """Use LLM to generate a friendly, engaging notification."""
        try:
            system_prompt = self._build_system_prompt()
            
            messages = [
                {
                    "role": "user",
                    "content": f"""Technical Warning to Convert:
Title: {warning.title}
Description: {warning.description}
Severity: {warning.severity}
Confidence: {warning.confidence}
Suggestions: {', '.join(warning.suggestions[:3]) if warning.suggestions else 'None'}

Please convert this technical warning into a friendly, encouraging notification that:
1. Uses warm, supportive language
2. Avoids technical jargon 
3. Creates curiosity rather than alarm
4. Maintains Ducky's educational and helpful personality
5. Ends with an invitation to learn more

Keep it concise (1-2 sentences) but engaging. The goal is to encourage the user to want to learn more about the issue rather than feeling overwhelmed."""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=200
            )
            
            notification = response.content[0].text.strip()
            
            self.logger.info(f"Generated notification: {notification[:100]}...")
            return notification
            
        except Exception as e:
            self.logger.error(f"LLM call failed in notification writing: {e}")
            # Fallback based on severity
            if warning.severity in ["high", "critical"]:
                return "Hey! I found something important in your code that could use some attention. Let's take a look together!"
            else:
                return "Hi there! I noticed something interesting in your recent changes. Want to chat about some potential improvements?"
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are a friendly and helpful technical communication specialist."

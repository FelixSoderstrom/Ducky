from typing import Optional, List
import json
from anthropic import Anthropic

from .base.rag_agent import RAGCapableAgent
from ..models.pipeline_models import PipelineResult, WarningMessage, AgentContext
from ...database.models import Dismissal


class NotificationAssessment(RAGCapableAgent):
    """Agent that checks user notification preferences based on dismissal history."""
    
    def __init__(self, api_key: str):
        super().__init__("NotificationAssessment", "notification_assessment")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze(self, context: AgentContext) -> tuple[PipelineResult, Optional[WarningMessage]]:
        """
        Check if user wants to be notified based on dismissal history.
        Can cancel pipeline if user has dismissed similar warnings.
        """
        self.logger.info("Starting notification assessment")
        
        if not context.current_warning:
            self.logger.warning("No warning message to assess")
            return PipelineResult.CONTINUE, context.current_warning
        
        try:
            # Query dismissal history
            dismissals = self.query_dismissals()
            
            if not dismissals:
                self.logger.info("No dismissal history found, continuing")
                return PipelineResult.CONTINUE, context.current_warning
            
            # Call LLM to analyze dismissal patterns
            should_notify = self._should_notify_user(context.current_warning, dismissals)
            
            if not should_notify:
                self.logger.info("User preferences suggest suppressing this notification")
                return PipelineResult.CANCEL, None
            
            return PipelineResult.CONTINUE, context.current_warning
            
        except Exception as e:
            self.logger.error(f"Notification assessment failed: {str(e)}")
            # On error, continue to be safe
            return PipelineResult.CONTINUE, context.current_warning
    
    def _should_notify_user(self, warning: WarningMessage, dismissals: List[Dismissal]) -> bool:
        """Use LLM to determine if user wants this notification based on dismissal history."""
        try:
            system_prompt = self._build_system_prompt()
            
            # Prepare dismissal history for LLM
            dismissal_summary = self._format_dismissal_history(dismissals)
            
            messages = [
                {
                    "role": "user",
                    "content": f"""
Current Warning:
Title: {warning.title}
Description: {warning.description}
Severity: {warning.severity}

DEVELOPERS previously dismissed warnings:
{dismissal_summary}

Based on the user's dismissal history, should we notify them about this current warning? 
Consider semantic similarity between the current warning and previously dismissed warnings.

Respond with JSON:
{{
    "should_notify": true/false,
    "reasoning": "Explanation of decision",
    "similarity_found": "Description of any similar dismissed warnings"
}}"""
                }
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=500
            )
            
            return self._parse_notification_decision(response.content[0].text)
            
        except Exception as e:
            self.logger.error(f"LLM call failed in notification assessment: {e}")
            # Default to notifying on error
            return True
    
    def _format_dismissal_history(self, dismissals: List[Dismissal]) -> str:
        """Format dismissal history for LLM consumption."""
        if not dismissals:
            return "No previous dismissals found."
        
        formatted = []
        for i, dismissal in enumerate(dismissals[-10:], 1):  # Last 10 dismissals
            formatted.append(f"""
Dismissal #{i}:
- Warning: {dismissal.warning[:200]}{'...' if len(dismissal.warning) > 200 else ''}
- Date: {dismissal.created_at}
""")
        
        return "\n".join(formatted)
    
    def _parse_notification_decision(self, response: str) -> bool:
        """Parse LLM response to extract notification decision."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
            else:
                response_data = json.loads(response)
            
            decision = response_data.get('should_notify', True)
            reasoning = response_data.get('reasoning', '')
            
            self.logger.info(f"Notification decision: {decision}, Reasoning: {reasoning}")
            return decision
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse notification decision: {e}")
            # Default to notifying on parse error
            return True
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from the JSON configuration."""
        return self.system_prompt or "You are a notification preference specialist."

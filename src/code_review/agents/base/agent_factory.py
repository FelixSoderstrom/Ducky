"""Factory for creating code review agent instances."""

from typing import List
from .base_agent import CodeReviewAgent


class AgentFactory:
    """Factory for creating and configuring code review agents."""
    
    @staticmethod
    def create_pipeline_agents(api_key: str) -> List[CodeReviewAgent]:
        """
        Create the standard pipeline agent chain.
        
        Args:
            api_key: API key for LLM-powered agents
            
        Returns:
            List of configured agents in pipeline order
        """
        # Import here to avoid circular imports
        from ..initial_assessment import InitialAssessment
        from ..notification_assessment import NotificationAssessment  
        from ..context_awareness import ContextAwareness
        from ..syntax_validation import SyntaxValidation
        from ..notification_writer import NotificationWriter
        from ..code_writer import CodeWriter
        
        return [
            InitialAssessment(api_key),
            NotificationAssessment(api_key),
            ContextAwareness(api_key),
            SyntaxValidation(api_key),
            NotificationWriter(api_key),
            CodeWriter(api_key)
        ] 
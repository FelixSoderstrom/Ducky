"""Output handling for pipeline results."""

import logging
from typing import Dict, Any, Optional

from ..models.pipeline_models import PipelineOutput

logger = logging.getLogger("ducky.pipeline.output")


class OutputHandler:
    """Handles pipeline output processing and conversion."""
    
    @staticmethod
    def handle_pipeline_output(output: PipelineOutput) -> Dict[str, Any]:
        """
        Handle the final pipeline output and return it as a dictionary.
        
        Args:
            output: The PipelineOutput containing notification, warning, solution AND context
            
        Returns:
            Dictionary containing the complete pipeline response data for RubberDuck
        """
        logger.info(f"Notification: {output.notification}")
        logger.info(f"Warning: {output.warning.title}")
        logger.info(f"Solution: Generated ({len(output.solution)} chars)")
        logger.info(f"File: {output.file_path}")
        logger.info(f"Project ID: {output.project_id}")
        
        # Also log to console for immediate feedback during development
        logger.debug(f"Pipeline output - Notification: {output.notification}")
        logger.debug(f"Pipeline output - Warning: {output.warning.title}")
        logger.debug(f"Pipeline output - Solution: Generated ({len(output.solution)} chars)")
        
        # Convert to dictionary for notification system - NOW WITH FULL CONTEXT
        response = {
            "notification": output.notification,
            "warning": {
                "title": output.warning.title,
                "severity": output.warning.severity,
                "description": output.warning.description,  # Now a list
                "suggestions": output.warning.suggestions,
                "affected_files": output.warning.affected_files,
                "confidence": output.warning.confidence,
                "metadata": output.warning.metadata,  # Now a list
                "full_description": output.warning.get_full_description(),
                "agent_contributions": output.warning.get_agent_contributions()
            },
            "solution": output.solution,
            # NEW: Full context for RubberDuck conversations and RAG
            "old_version": output.old_version,
            "new_version": output.new_version,
            "file_path": output.file_path,
            "project_id": output.project_id
        }
        
        return response 
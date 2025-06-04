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
            output: The PipelineOutput containing notification, warning, and solution
            
        Returns:
            Dictionary containing the pipeline response data
        """
        logger.info(f"Notification: {output.notification}")
        logger.info(f"Warning: {output.warning.title}")
        logger.info(f"Solution: {output.solution}")
        
        # Also log to console for immediate feedback during development
        logger.debug(f"Pipeline output - Notification: {output.notification}")
        logger.debug(f"Pipeline output - Warning: {output.warning.title}")
        logger.debug(f"Pipeline output - Solution: {output.solution}")
        
        # Convert to dictionary for notification system
        response = {
            "notification": output.notification,
            "warning": {
                "title": output.warning.title,
                "severity": output.warning.severity,
                "description": output.warning.description,
                "suggestions": output.warning.suggestions,
                "affected_files": output.warning.affected_files,
                "confidence": output.warning.confidence,
                "metadata": output.warning.metadata
            },
            "solution": output.solution
        }
        
        return response 
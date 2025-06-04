"""
Legacy pipeline interface for backward compatibility.

This file maintains the original public interface while delegating to the new
modular architecture. All functionality has been moved to specialized modules:

- Data structures: src/code_review/models/
- Agent base classes: src/code_review/agents/base/
- Pipeline execution: src/code_review/pipeline/
- Utilities: src/code_review/utils/prompt_loader.py, logging_utils.py
"""

import asyncio
import logging
import concurrent.futures
from typing import Dict, Any, List, Optional

from sqlalchemy import select

from ...watcher.compare_versions import FileChange
from ...database.session import get_db
from ...database.models import Project
from ..models.pipeline_models import (
    PipelineResult,
    WarningMessage, 
    PipelineOutput,
    AgentContext
)
from ..pipeline.pipeline_executor import CodeReviewPipeline
from ..pipeline.output_handler import OutputHandler

# Legacy exports for backward compatibility
__all__ = [
    "PipelineResult",
    "WarningMessage", 
    "PipelineOutput", 
    "AgentContext",
    "CodeReviewPipeline",
    "code_review_pipeline"
]


async def code_review_pipeline(changes: List[FileChange], project_id: int) -> Optional[Dict[str, Any]]:
    """Process code changes and generate review feedback using agent pipeline.
    
    This is the main entry point for the code review pipeline, maintained for
    backward compatibility with the existing system.
    """
    
    if not changes:
        return None
    
    # Get API key from the project in database
    with get_db() as session:
        stmt = select(Project).where(Project.id == project_id)
        result = session.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            logging.error(f"Project {project_id} not found")
            return None
        
        api_key = project.anthropic_key
    
    # Run the pipeline in a thread pool to avoid blocking the event loop
    def run_pipeline():
        pipeline = CodeReviewPipeline(api_key)
        return pipeline.execute(changes, project_id)
    
    # Execute pipeline in thread pool
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, run_pipeline)
    
    if result:
        return OutputHandler.handle_pipeline_output(result)
    else:
        logging.info("No issues found - pipeline was cancelled")
        return None
"""Pipeline context management for code review execution."""

import logging
from typing import List, Optional

from ..models.pipeline_models import AgentContext
from ...watcher.compare_versions import FileChange

logger = logging.getLogger("ducky.pipeline.context")
cr_logger = logging.getLogger("code_review")


class PipelineContextManager:
    """Manages pipeline execution context and validation."""
    
    @staticmethod
    def create_context_from_changes(changes: List[FileChange], project_id: int) -> Optional[AgentContext]:
        """
        Create AgentContext from file changes with validation.
        
        Args:
            changes: List of FileChange objects
            project_id: ID of the project being analyzed
            
        Returns:
            AgentContext if valid, None if invalid or should skip
        """
        if not changes:
            return None
        
        # For now, process only the first change
        change = changes[0]
        
        # Log file information to code review log
        cr_logger.info("=" * 80)
        cr_logger.info(f"CODE REVIEW PIPELINE STARTING")
        cr_logger.info("=" * 80)
        cr_logger.info(f"File: {change['path']}")
        cr_logger.info(f"Project ID: {project_id}")
        cr_logger.info(f"Is New File: {change.get('is_new_file', False)}")
        cr_logger.info(f"Last Edit: {change.get('last_edit', 'Unknown')}")
        cr_logger.info("-" * 80)
        
        # Validate that we have meaningful content to analyze
        old_version = change.get('old_version', "")
        new_version = change.get('new_version', "")
        
        if not PipelineContextManager._is_valid_content(change, old_version, new_version):
            return None
        
        # Log content preview
        PipelineContextManager._log_content_preview(old_version, new_version)
        
        return AgentContext(
            old_version=old_version,
            new_version=new_version,
            file_path=change['path'],
            project_id=project_id
        )
    
    @staticmethod
    def _is_valid_content(change: FileChange, old_version: str, new_version: str) -> bool:
        """Validate that content is meaningful for analysis."""
        file_path = change['path']
        
        if not old_version and not new_version:
            cr_logger.warning(f"No content found for file {file_path} - skipping pipeline")
            logger.warning(f"No content found for file {file_path} - skipping pipeline")
            return False
        
        # For new files, old_version can be empty, but new_version should have content
        if change.get('is_new_file', False) and not new_version.strip():
            cr_logger.warning(f"New file {file_path} has no content - skipping pipeline")
            logger.warning(f"New file {file_path} has no content - skipping pipeline")
            return False
        
        # For existing files, we should have both versions (unless it's a deletion)
        if not change.get('is_new_file', False) and not old_version and not new_version:
            cr_logger.warning(f"No content versions found for {file_path} - skipping pipeline")
            logger.warning(f"No content versions found for {file_path} - skipping pipeline") 
            return False
        
        return True
    
    @staticmethod
    def _log_content_preview(old_version: str, new_version: str):
        """Log content preview for debugging."""
        cr_logger.info(f"Content Analysis:")
        cr_logger.info(f"  ├─ Old Version: {len(old_version)} characters")
        if old_version:
            preview_old = old_version[:200].replace('\n', '\\n')
            ellipsis = '...' if len(old_version) > 200 else ''
            cr_logger.info(f"  │   Preview: {preview_old}{ellipsis}")
        cr_logger.info(f"  └─ New Version: {len(new_version)} characters")
        if new_version:
            preview_new = new_version[:200].replace('\n', '\\n')
            ellipsis = '...' if len(new_version) > 200 else ''
            cr_logger.info(f"      Preview: {preview_new}{ellipsis}") 
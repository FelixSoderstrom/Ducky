# This file is the main pipeline for LLM code review
# Call agents from here one at a time.
# Agent definition and API calls are made in their respective file/classes.

from typing import Dict, Any, List
from src.watcher.compare_versions import FileChange


def code_review_pipeline(changes: List[FileChange]) -> None:
    """Process code changes and generate review feedback.
    
    Args:
        changes: List of FileChange objects containing old and new versions of changed files
    """
    # Implementation will be added in future steps
    pass
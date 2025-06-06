"""Base class for agents with RAG (Retrieval-Augmented Generation) capabilities."""

from typing import List
from sqlalchemy import select

from .base_agent import CodeReviewAgent
from ....database.session import get_db
from ....database.models import Dismissal, File


class RAGCapableAgent(CodeReviewAgent):
    """Base class for agents that need RAG capabilities."""
    
    def query_dismissals(self) -> List[Dismissal]:
        """Query all dismissed notifications from database."""
        with get_db() as session:
            stmt = select(Dismissal)
            result = session.execute(stmt)
            return result.scalars().all()
    
    def query_single_file(self, project_id: int, file_path: str) -> File:
        """
        Query a single file by path with full content.
        
        Args:
            project_id: Project ID to search within
            file_path: Exact path of the file to retrieve
            
        Returns:
            File object with full content, or None if not found
        """
        with get_db() as session:
            stmt = select(File).where(
                File.project_id == project_id,
                File.path == file_path
            )
            result = session.execute(stmt)
            return result.scalar_one_or_none()
    
    def search_files_by_pattern(self, project_id: int, pattern: str, max_results: int = 10) -> List[File]:
        """
        Search for files matching a pattern (useful for finding related files).
        Returns file metadata only - use query_single_file() to get full content.
        
        Args:
            project_id: Project ID to search within
            pattern: Pattern to match in file paths (e.g., "calculator", "*.py")
            max_results: Maximum number of results to return
            
        Returns:
            List of File objects (metadata only, no content)
        """
        with get_db() as session:
            stmt = select(File).where(
                File.project_id == project_id,
                File.path.contains(pattern)
            ).limit(max_results)
            result = session.execute(stmt)
            # Return actual File objects from database (content will be loaded if accessed)
            return result.scalars().all() 
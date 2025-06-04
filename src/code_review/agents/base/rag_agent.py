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
    
    def query_project_files(self, project_id: int, exclude_path: str = None) -> List[File]:
        """Query files from the same project."""
        with get_db() as session:
            stmt = select(File).where(File.project_id == project_id)
            if exclude_path:
                stmt = stmt.where(File.path != exclude_path)
            result = session.execute(stmt)
            return result.scalars().all() 
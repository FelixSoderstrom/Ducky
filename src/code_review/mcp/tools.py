"""Context7 MCP tool calling utilities."""

import logging
from typing import Optional

from mcp import ClientSession


class Context7Tools:
    """Handles Context7 MCP tool calls."""
    
    def __init__(self):
        """Initialize Context7 tools handler."""
        self.logger = logging.getLogger("ducky.mcp.tools")
    
    async def resolve_library_id(self, session: ClientSession, library_name: str) -> Optional[str]:
        """
        Resolve library name to Context7-compatible ID using MCP tools.
        
        Args:
            session: Active MCP session
            library_name: Name of the library (e.g., "fastapi", "sqlalchemy")
            
        Returns:
            Context7-compatible library ID or None if resolution fails
        """
        try:
            # Call Context7 resolve-library-id tool
            result = await session.call_tool(
                "resolve-library-id",
                {"libraryName": library_name}
            )
            
            if result.content and len(result.content) > 0:
                library_id = result.content[0].text.strip()
                self.logger.info(f"Resolved '{library_name}' to '{library_id}'")
                return library_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to resolve library ID for '{library_name}': {str(e)}")
            return None
    
    async def get_library_docs(self, session: ClientSession, library_id: str, 
                              topic: Optional[str] = None, tokens: int = 5000) -> Optional[str]:
        """
        Get documentation for a library using MCP tools.
        
        Args:
            session: Active MCP session
            library_id: Context7-compatible library ID
            topic: Optional topic to focus on (e.g., "best practices", "syntax")
            tokens: Maximum tokens to return (default: 5000)
            
        Returns:
            Documentation content or None if retrieval fails
        """
        try:
            # Prepare parameters
            params = {
                "context7CompatibleLibraryID": library_id,
                "tokens": tokens
            }
            if topic:
                params["topic"] = topic
            
            # Call Context7 get-library-docs tool
            result = await session.call_tool("get-library-docs", params)
            
            if result.content and len(result.content) > 0:
                docs = result.content[0].text
                self.logger.info(f"Retrieved {len(docs)} chars of documentation for '{library_id}' | topic: {topic}")
                return docs
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get docs for '{library_id}': {str(e)}")
            return None 
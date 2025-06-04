"""Base class for agents with MCP (Model Context Protocol) capabilities."""

from .base_agent import CodeReviewAgent


class MCPCapableAgent(CodeReviewAgent):
    """Base class for agents that need MCP server integration."""
    
    def query_documentation(self, query: str) -> str:
        """
        Query MCP server for documentation.
        
        Args:
            query: Documentation query string
            
        Returns:
            Documentation response or empty string if not available
        """
        # TODO: Implement MCP server integration
        # This is left open-ended for future implementation
        self.logger.info(f"MCP query: {query}")
        return "" 
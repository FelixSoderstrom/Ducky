"""Base class for agents that can use MCP (Model Context Protocol) services."""

from .base_agent import CodeReviewAgent
from src.services.documentation_service import DocumentationService


class MCPCapableAgent(CodeReviewAgent):
    """Base class for agents that can use MCP services like Context7."""
    
    def __init__(self, name: str, agent_type: str):
        """Initialize MCP-capable agent with documentation service."""
        super().__init__(name, agent_type)
        
        # Initialize DocumentationService for Context7 integration
        self.doc_service = DocumentationService()
        self.logger.info(f"MCP-capable agent {name} initialized with DocumentationService")
    
    def query_documentation(self, query: str) -> str:
        """
        Query MCP server for documentation.
        
        Args:
            query: Documentation query string
            
        Returns:
            Documentation response or fallback message if server unavailable
        """
        self.logger.info(f"MCP query: {query}")
        
        try:
            # Use the sync wrapper from DocumentationService
            return self.doc_service.get_documentation_sync(query)
        
        except Exception as e:
            self.logger.error(f"MCP documentation query failed: {str(e)}")
            return f"""Context7 MCP Server Status: UNAVAILABLE (Error: {str(e)})

The agent cannot access real-time documentation and will provide analysis based on general programming knowledge.

Original query: {query}

Note: For the most accurate documentation-based analysis, ensure the Context7 MCP server is running and accessible.""" 
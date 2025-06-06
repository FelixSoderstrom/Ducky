"""High-level documentation service orchestrating Context7 MCP integration."""

import logging
import asyncio
import concurrent.futures
from typing import List

from src.utils.cache_manager import CacheManager
from src.utils.code_analyzer import CodeAnalyzer
from src.utils.query_builder import QueryBuilder
from src.code_review.mcp.connection import MCPConnection
from src.code_review.mcp.tools import Context7Tools


class DocumentationService:
    """High-level service for Context7 documentation retrieval and caching."""
    
    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize documentation service.
        
        Args:
            cache_ttl_seconds: Cache TTL for documentation (default: 1 hour)
        """
        self.logger = logging.getLogger("ducky.services.documentation")
        self.cache = CacheManager(ttl_seconds=cache_ttl_seconds)
        self.connection = MCPConnection()
        self.tools = Context7Tools()
    
    def get_documentation_sync(self, query: str) -> str:
        """
        Get documentation for a natural language query with caching (sync wrapper).
        
        Args:
            query: Natural language query for documentation
            
        Returns:
            Documentation content or fallback message
        """
        # Check cache first
        cache_key = self.cache.get_cache_key(query)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.logger.debug(f"Cache hit for query: {query[:50]}...")
            return cached_result
        
        # Run async operation in event loop
        try:
            result = self._run_async_in_sync(self._get_documentation_async(query))
            self.cache.set(cache_key, result)
            return result
        except Exception as e:
            self.logger.error(f"Documentation retrieval failed: {str(e)}")
            fallback = self._generate_fallback_message(query, reason=f"Error: {str(e)}")
            self.cache.set(cache_key, fallback)
            return fallback
    
    async def get_documentation(self, query: str) -> str:
        """
        Get documentation for a natural language query with caching (async version).
        
        Args:
            query: Natural language query for documentation
            
        Returns:
            Documentation content or fallback message
        """
        # Check cache first
        cache_key = self.cache.get_cache_key(query)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.logger.debug(f"Cache hit for query: {query[:50]}...")
            return cached_result
        
        try:
            result = await self._get_documentation_async(query)
            self.cache.set(cache_key, result)
            return result
        except Exception as e:
            self.logger.error(f"Documentation retrieval failed: {str(e)}")
            fallback = self._generate_fallback_message(query, reason=f"Error: {str(e)}")
            self.cache.set(cache_key, fallback)
            return fallback
    
    async def _get_documentation_async(self, query: str) -> str:
        """Internal async implementation for documentation retrieval."""
        # Connect if needed
        connected = await self.connection.connect()
        if not connected:
            return self._generate_fallback_message(query, reason="Server unavailable")
        
        try:
            # Extract libraries from query
            libraries = CodeAnalyzer.extract_libraries_from_query(query)
            
            if not libraries:
                fallback = self._generate_fallback_message(query, reason="No libraries detected in query")
                return fallback
            
            # Retrieve documentation for each library
            documentation_parts = []
            
            async with self.connection.get_session_context() as session:
                for library in libraries:
                    # Resolve library ID
                    library_id = await self.tools.resolve_library_id(session, library)
                    if not library_id:
                        self.logger.warning(f"Could not resolve library: {library}")
                        continue
                    
                    # Extract topic from query
                    topic = QueryBuilder.extract_topic_from_query(query, library)
                    
                    # Get documentation
                    docs = await self.tools.get_library_docs(session, library_id, topic=topic)
                    if docs:
                        documentation_parts.append(f"## {library.upper()} Documentation\n{docs}")
            
            # Format result
            if documentation_parts:
                return "\n\n".join(documentation_parts)
            else:
                return self._generate_fallback_message(query, reason="No documentation retrieved")
        
        except Exception as e:
            self.logger.error(f"Error in documentation retrieval: {str(e)}")
            return self._generate_fallback_message(query, reason=f"Error: {str(e)}")
        finally:
            await self.connection.disconnect()
    
    def get_targeted_documentation_sync(self, file_path: str, code: str, warning_text: str) -> str:
        """
        Get targeted documentation based on code analysis and warning context (sync wrapper).
        
        Args:
            file_path: Path to the code file
            code: Code content to analyze
            warning_text: Warning title and description
            
        Returns:
            Targeted documentation content
        """
        try:
            return self._run_async_in_sync(self.get_targeted_documentation(file_path, code, warning_text))
        except Exception as e:
            self.logger.error(f"Targeted documentation retrieval failed: {str(e)}")
            return self._generate_fallback_message(f"Code analysis for {file_path}", reason=f"Error: {str(e)}")
    
    async def get_targeted_documentation(self, file_path: str, code: str, warning_text: str) -> str:
        """
        Get targeted documentation based on code analysis and warning context.
        
        Args:
            file_path: Path to the code file
            code: Code content to analyze
            warning_text: Warning title and description
            
        Returns:
            Targeted documentation content
        """
        # Analyze code
        language = CodeAnalyzer.detect_language(file_path, code)
        libraries = CodeAnalyzer.extract_libraries(code, language)
        issue_types = QueryBuilder.categorize_warning_issues(warning_text)
        
        # Build targeted query
        query = QueryBuilder.build_documentation_query(language, libraries, issue_types)
        
        # Get documentation
        return await self.get_documentation(query)
    
    def _run_async_in_sync(self, coro):
        """
        Run async coroutine in sync context safely.
        
        This handles the common patterns needed for running async MCP operations
        within the synchronous pipeline.
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context already (like in a ThreadPoolExecutor)
                # Create a new event loop in a thread
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result(timeout=30)  # 30 second timeout
            else:
                # No running loop, we can use it directly
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(coro)
    
    def _generate_fallback_message(self, query: str, reason: str = "Server unavailable") -> str:
        """Generate fallback message when Context7 is not available."""
        return f"""Context7 MCP Server Status: UNAVAILABLE ({reason})

The DocumentationValidator cannot access real-time documentation and will provide analysis based on general programming knowledge.

Original query: {query}

Note: For the most accurate syntax and best practice analysis, ensure the Context7 MCP server is running and accessible."""
    
    async def disconnect(self) -> None:
        """Disconnect from Context7 MCP server."""
        await self.connection.disconnect()
    
    def clear_cache(self) -> None:
        """Clear documentation cache."""
        self.cache.clear()
        self.logger.info("Documentation cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": self.cache.size(),
            "max_entries": self.cache.max_entries,
            "ttl_seconds": self.cache.ttl_seconds
        } 
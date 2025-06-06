"""Pure MCP connection management for Context7 server."""

import logging
import asyncio
import shutil
import os
from typing import Optional
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPConnection:
    """Handles pure MCP connection to Context7 server."""
    
    def __init__(self):
        """Initialize MCP connection handler."""
        self.logger = logging.getLogger("ducky.mcp.connection")
        self.session: Optional[ClientSession] = None
        self.connected = False
        self._connection_context = None
        
        # Find npx executable path
        self.npx_path = self._find_npx_executable()
        
        # Context7 server parameters with fallback options
        self.server_configs = self._build_server_configs()
    
    def _find_npx_executable(self) -> Optional[str]:
        """Find the npx executable on the system."""
        # Try common Windows locations first
        common_paths = [
            "C:/Program Files/nodejs/npx.cmd",
            "C:/Program Files/nodejs/npx",
            "C:/Program Files (x86)/nodejs/npx.cmd", 
            "C:/Program Files (x86)/nodejs/npx"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                self.logger.info(f"Found npx at: {path}")
                return path
        
        # Fallback to system PATH search
        npx_path = shutil.which("npx")
        if npx_path:
            self.logger.info(f"Found npx via PATH: {npx_path}")
            return npx_path
        
        self.logger.warning("npx not found in common locations or PATH")
        return None
    
    def _build_server_configs(self) -> list:
        """Build server configuration list based on available executables."""
        configs = []
        
        if self.npx_path:
            # Primary configuration with found npx
            configs.append(StdioServerParameters(
                command=self.npx_path,
                args=["-y", "@upstash/context7-mcp@latest"]
            ))
            
            # Fallback configurations with different npx options
            configs.append(StdioServerParameters(
                command=self.npx_path,
                args=["-y", "--node-options=--experimental-vm-modules", "@upstash/context7-mcp@latest"]
            ))
            
            configs.append(StdioServerParameters(
                command=self.npx_path,
                args=["-y", "--node-options=--experimental-fetch", "@upstash/context7-mcp@latest"]
            ))
        
        # Try bunx as fallback if available
        bunx_path = shutil.which("bunx")
        if bunx_path:
            configs.append(StdioServerParameters(
                command=bunx_path,
                args=["-y", "@upstash/context7-mcp"]
            ))
        
        # Last resort: try basic npx command (might work in some environments)
        configs.append(StdioServerParameters(
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"]
        ))
        
        return configs
    
    @asynccontextmanager
    async def _create_session(self, server_params):
        """Create a properly managed MCP session."""
        async with stdio_client(server_params) as (read_stream, write_stream):
            session = ClientSession(read_stream, write_stream)
            async with session:
                yield session
    
    async def connect(self) -> bool:
        """
        Connect to Context7 MCP server with fallback mechanisms.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.server_configs:
            self.logger.error("No valid server configurations found. Is Node.js installed?")
            return False
        
        self.logger.info("Connecting to Context7 MCP server...")
        
        for i, server_params in enumerate(self.server_configs):
            try:
                self.logger.debug(f"Trying connection method {i+1}/{len(self.server_configs)}: {server_params.command} {' '.join(server_params.args)}")
                
                # Test connection with this configuration
                async with self._create_session(server_params) as session:
                    # Test the connection by listing tools
                    result = await session.list_tools()
                    self.logger.info(f"Context7 connected successfully using method {i+1}. Available tools: {[tool.name for tool in result.tools]}")
                    
                    # Store successful configuration for future use
                    self.successful_config = server_params
                    self.connected = True
                    return True
                    
            except Exception as e:
                self.logger.warning(f"Connection method {i+1} failed: {str(e)}")
                continue
        
        self.logger.error("Failed to connect to Context7 MCP server with all methods")
        self.logger.info("Troubleshooting tips:")
        self.logger.info("1. Ensure Node.js is installed and in PATH")
        self.logger.info("2. Try running manually: npx -y @upstash/context7-mcp@latest")
        self.logger.info("3. Check if corporate firewall is blocking npm downloads")
        self.connected = False
        return False
    
    @asynccontextmanager
    async def get_session_context(self):
        """Get a session context manager for making requests."""
        if not hasattr(self, 'successful_config'):
            raise ConnectionError("Must connect successfully before getting session")
        
        async with self._create_session(self.successful_config) as session:
            yield session
    
    async def disconnect(self) -> None:
        """Disconnect from Context7 MCP server."""
        # With the new pattern, connections are automatically cleaned up
        # by the async context managers
        if self.connected:
            self.logger.info("Disconnected from Context7 MCP server")
        self.connected = False
        if hasattr(self, 'successful_config'):
            delattr(self, 'successful_config')
    
    def is_connected(self) -> bool:
        """Check if MCP connection is available."""
        return self.connected and hasattr(self, 'successful_config')
    
    async def test_connection(self) -> bool:
        """Test if we can establish a connection without storing state."""
        try:
            return await self.connect()
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False 
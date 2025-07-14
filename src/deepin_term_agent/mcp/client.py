"""MCP protocol client implementation."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import websockets
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPMessage(BaseModel):
    """Base MCP message format."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(alias="inputSchema")


class MCPClient:
    """MCP protocol client for connecting to MCP servers."""
    
    def __init__(self, server_url: str, name: str = "deepin-term-agent", version: str = "0.1.0"):
        self.server_url = server_url
        self.name = name
        self.version = version
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.tools: List[MCPTool] = []
        self._message_id = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def connect(self) -> bool:
        """Connect to MCP server."""
        try:
            logger.info(f"Connecting to MCP server at {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            
            # Initialize connection
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": self.name, "version": self.version}
            })
            
            # Get tools list
            tools_response = await self._send_request("tools/list", {})
            if tools_response and "tools" in tools_response:
                self.tools = [MCPTool(**tool) for tool in tools_response["tools"]]
                logger.info(f"Loaded {len(self.tools)} tools from server")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from MCP server")

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a request to the MCP server."""
        if not self.websocket:
            raise RuntimeError("Not connected to MCP server")

        message_id = str(self._message_id)
        self._message_id += 1

        message = MCPMessage(id=message_id, method=method, params=params)
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[message_id] = future

        try:
            await self.websocket.send(message.model_dump_json())
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response to {method}")
            raise
        finally:
            self._pending_requests.pop(message_id, None)

    async def _handle_messages(self):
        """Handle incoming messages from the server."""
        if not self.websocket:
            return

        async for raw_message in self.websocket:
            try:
                message_data = json.loads(raw_message)
                message = MCPMessage(**message_data)
                
                if message.id and message.id in self._pending_requests:
                    future = self._pending_requests.pop(message.id)
                    if not future.done():
                        if message.error:
                            future.set_exception(Exception(message.error.get("message", "Unknown error")))
                        else:
                            future.set_result(message.result)
                            
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")

        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        return response

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def list_tools(self) -> List[MCPTool]:
        """List all available tools."""
        return self.tools.copy()
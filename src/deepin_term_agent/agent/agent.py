"""Main agent implementation for handling user input and tool execution."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from ..mcp.client import MCPClient
from ..tools.builtin import BUILTIN_TOOLS
from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Handles tool execution for both built-in and MCP tools."""
    
    def __init__(self):
        self.mcp_clients: Dict[str, MCPClient] = {}
        self.config_manager = ConfigManager()
    
    async def initialize(self):
        """Initialize MCP connections."""
        config = self.config_manager.load_config()
        mcp_servers = config.get("mcp_servers", {})
        
        for server_name, server_config in mcp_servers.items():
            if server_config.get("enabled", True):
                try:
                    client = MCPClient(
                        server_config["url"],
                        name="deepin-term-agent",
                        version="0.1.0"
                    )
                    
                    if await client.connect():
                        self.mcp_clients[server_name] = client
                        logger.info(f"Connected to MCP server: {server_name}")
                    else:
                        logger.warning(f"Failed to connect to MCP server: {server_name}")
                        
                except Exception as e:
                    logger.error(f"Error connecting to MCP server {server_name}: {e}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools (built-in + MCP)."""
        tools = []
        
        # Add built-in tools
        for tool_name, tool_info in BUILTIN_TOOLS.items():
            tools.append({
                "name": tool_info["name"],
                "description": tool_info["description"],
                "type": "builtin",
                "schema": tool_info["schema"]
            })
        
        # Add MCP tools
        for server_name, client in self.mcp_clients.items():
            try:
                mcp_tools = client.list_tools()
                for tool in mcp_tools:
                    tools.append({
                        "name": f"{server_name}.{tool.name}",
                        "description": tool.description,
                        "type": "mcp",
                        "server": server_name,
                        "schema": tool.input_schema
                    })
            except Exception as e:
                logger.error(f"Error listing tools from {server_name}: {e}")
        
        return tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        
        # Check built-in tools first
        if tool_name in BUILTIN_TOOLS:
            tool_info = BUILTIN_TOOLS[tool_name]
            return await tool_info["execute"](arguments)
        
        # Check MCP tools
        for server_name, client in self.mcp_clients.items():
            if tool_name.startswith(f"{server_name}."):
                actual_tool_name = tool_name[len(server_name) + 1:]
                return await client.call_tool(actual_tool_name, arguments)
        
        # Try exact match in MCP tools
        for server_name, client in self.mcp_clients.items():
            tool = client.get_tool(tool_name)
            if tool:
                return await client.call_tool(tool_name, arguments)
        
        raise ValueError(f"Tool not found: {tool_name}")


class TerminalAgent:
    """Main terminal agent that processes user messages and manages tool execution."""
    
    def __init__(self):
        self.tool_executor = ToolExecutor()
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = """You are a helpful terminal assistant with access to various tools.
        
You can use the following tools to help users:
- run_command: Execute shell commands
- read_file: Read file contents
- write_file: Write content to files
- read_logs: Read log files with filtering
- list_directory: List directory contents

Always provide clear explanations of what you're doing and show the results of tool usage.
When using tools, be specific about the parameters you're using.
"""
    
    async def initialize(self):
        """Initialize the agent."""
        await self.tool_executor.initialize()
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return await self.tool_executor.list_tools()
    
    async def process_message(self, message: str) -> str:
        """Process a user message and return a response."""
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Simple command parsing for now
        # In a real implementation, this would use an LLM to determine tool usage
        response = await self._handle_simple_command(message)
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    async def _handle_simple_command(self, message: str) -> str:
        """Handle simple commands using basic parsing."""
        message = message.strip()
        
        # Simple command patterns
        if message.startswith("run "):
            command = message[4:].strip()
            result = await self.tool_executor.execute_tool("run_command", {"command": command})
            return self._format_command_result(result, command)
        
        elif message.startswith("read "):
            file_path = message[5:].strip()
            result = await self.tool_executor.execute_tool("read_file", {"file_path": file_path})
            return self._format_file_result(result, file_path)
        
        elif message.startswith("write "):
            # write /path/to/file\ncontent
            parts = message[6:].split("\n", 1)
            if len(parts) != 2:
                return "Usage: write /path/to/file\ncontent"
            
            file_path, content = parts
            result = await self.tool_executor.execute_tool("write_file", {
                "file_path": file_path.strip(),
                "content": content
            })
            return self._format_write_result(result, file_path)
        
        elif message.startswith("ls"):
            directory = message[2:].strip() or "."
            result = await self.tool_executor.execute_tool("list_directory", {
                "directory": directory
            })
            return self._format_ls_result(result, directory)
        
        elif message.startswith("logs "):
            file_path = message[5:].strip()
            result = await self.tool_executor.execute_tool("read_logs", {
                "file_path": file_path,
                "lines": 50
            })
            return self._format_logs_result(result, file_path)
        
        else:
            # General help
            tools = await self.list_tools()
            tool_list = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in tools])
            
            return f"""I can help you with various terminal tasks. Available tools:

{tool_list}

Usage examples:
- run ls -la /tmp
- read /etc/hosts
- write /tmp/test.txt\nHello World
- ls /var/log
- logs /var/log/syslog"""
    
    def _format_command_result(self, result: Dict[str, Any], command: str) -> str:
        """Format command execution results."""
        if result["success"]:
            output = []
            if result["stdout"]:
                output.append(f"STDOUT:\n{result['stdout']}")
            if result["stderr"]:
                output.append(f"STDERR:\n{result['stderr']}")
            
            return f"Command completed (exit code: {result['return_code']})\n" + "\n\n".join(output)
        else:
            return f"Command failed: {result.get('error', 'Unknown error')}"
    
    def _format_file_result(self, result: Dict[str, Any], file_path: str) -> str:
        """Format file reading results."""
        if result["success"]:
            return f"File: {result['file_path']}\nSize: {result['size']} bytes\n\n{result['content']}"
        else:
            return f"Error reading file: {result.get('error', 'Unknown error')}"
    
    def _format_write_result(self, result: Dict[str, Any], file_path: str) -> str:
        """Format file writing results."""
        if result["success"]:
            return f"Successfully wrote {result['size']} bytes to {result['file_path']}"
        else:
            return f"Error writing file: {result.get('error', 'Unknown error')}"
    
    def _format_ls_result(self, result: Dict[str, Any], directory: str) -> str:
        """Format directory listing results."""
        if result["success"]:
            items = result["items"]
            output = [f"Directory: {result['directory']} ({result['total']} items)"]
            
            for item in items[:20]:  # Limit to first 20 items
                if item["type"] == "directory":
                    output.append(f"  📁 {item['name']}/")
                else:
                    size_str = self._format_size(item["size"])
                    output.append(f"  📄 {item['name']} ({size_str})")
            
            if len(items) > 20:
                output.append(f"  ... and {len(items) - 20} more items")
            
            return "\n".join(output)
        else:
            return f"Error listing directory: {result.get('error', 'Unknown error')}"
    
    def _format_logs_result(self, result: Dict[str, Any], file_path: str) -> str:
        """Format log reading results."""
        if result["success"]:
            return f"Log file: {result['file_path']}\nLines: {result['lines']}\n\n{result['content']}"
        else:
            return f"Error reading logs: {result.get('error', 'Unknown error')}"
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    async def cleanup(self):
        """Cleanup resources."""
        # Disconnect MCP clients
        for client in self.tool_executor.mcp_clients.values():
            await client.disconnect()
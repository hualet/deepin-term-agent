"""Main agent implementation for handling user input and tool execution."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from ..mcp.client import MCPClient
from ..tools.builtin import BUILTIN_TOOLS
from ..config.manager import ConfigManager
from ..llm.client import MoonshotClient

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
        self.llm_client: Optional[MoonshotClient] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.config_manager = ConfigManager()
        self.system_prompt = """You are an intelligent terminal assistant powered by Moonshot K2 AI. You have access to powerful terminal tools to help users efficiently manage their system.

Available tools:
- run_command: Execute shell commands with safety checks
- read_file: Read and analyze file contents
- write_file: Create or modify files
- read_logs: Read and filter log files
- list_directory: Explore directory structures

Guidelines:
1. Always understand the user's intent before executing commands
2. Provide clear explanations of what you're doing
3. Show command outputs when relevant
4. Suggest better approaches when you see opportunities
5. Be concise but informative
6. Handle errors gracefully and provide helpful suggestions
7. Use appropriate commands for the task (e.g., use 'ls -la' for detailed listings)
8. Consider safety implications of commands

When users ask for help, provide both the solution and explain why it's the right approach.
For complex requests, break them down into clear steps.
"""

    async def initialize(self):
        """Initialize the agent."""
        await self.tool_executor.initialize()

        # Initialize LLM client
        config = self.config_manager.load_config()
        llm_config = config.get("llm", {})

        try:
            api_key = llm_config.get("api_key") or os.getenv("MOONSHOT_API_KEY")
            if api_key:
                self.llm_client = MoonshotClient(
                    api_key=api_key,
                    base_url=llm_config.get("base_url", "https://api.moonshot.cn/v1")
                )
                logger.info("Initialized Moonshot K2 LLM client")
            else:
                logger.warning("No Moonshot API key found. LLM features disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.llm_client = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return await self.tool_executor.list_tools()

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response using LLM intelligence."""

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

        if self.llm_client:
            # Use LLM for intelligent processing
            response = await self._handle_llm_command(message)
        else:
            # Fallback to simple command parsing
            response = await self._handle_simple_command(message)

        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    async def _handle_llm_command(self, message: str) -> str:
        """Handle commands using Moonshot K2 LLM with intelligent tool selection."""
        try:
            # Get available tools in OpenAI function calling format
            tools = await self.list_tools()
            llm_tools = []

            for tool in tools:
                if tool["type"] == "builtin":
                    # Map builtin tools to LLM function format
                    if tool["name"] == "run_command":
                        llm_tools.append({
                            "type": "function",
                            "function": {
                                "name": "run_command",
                                "description": "Execute a shell command",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "command": {
                                            "type": "string",
                                            "description": "The shell command to execute"
                                        }
                                    },
                                    "required": ["command"]
                                }
                            }
                        })
                    elif tool["name"] == "read_file":
                        llm_tools.append({
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "description": "Read the contents of a file",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "Path to the file to read"
                                        }
                                    },
                                    "required": ["file_path"]
                                }
                            }
                        })
                    elif tool["name"] == "write_file":
                        llm_tools.append({
                            "type": "function",
                            "function": {
                                "name": "write_file",
                                "description": "Write content to a file",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "Path to the file to write"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Content to write to the file"
                                        }
                                    },
                                    "required": ["file_path", "content"]
                                }
                            }
                        })
                    elif tool["name"] == "list_directory":
                        llm_tools.append({
                            "type": "function",
                            "function": {
                                "name": "list_directory",
                                "description": "List contents of a directory",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "directory": {
                                            "type": "string",
                                            "description": "Directory path to list"
                                        }
                                    },
                                    "required": ["directory"]
                                }
                            }
                        })
                    elif tool["name"] == "read_logs":
                        llm_tools.append({
                            "type": "function",
                            "function": {
                                "name": "read_logs",
                                "description": "Read log files with filtering options",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "Path to the log file"
                                        },
                                        "lines": {
                                            "type": "integer",
                                            "description": "Number of lines to read (default: 50)"
                                        },
                                        "filter": {
                                            "type": "string",
                                            "description": "Optional filter pattern"
                                        }
                                    },
                                    "required": ["file_path"]
                                }
                            }
                        })
                elif tool["type"] == "mcp":
                    # Add MCP tools with their schemas
                    llm_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["schema"]
                        }
                    })

            # Get recent conversation history (last 10 messages)
            recent_history = self.conversation_history[-10:-1] if len(self.conversation_history) > 1 else []

            # Generate response using LLM
            response = await self.llm_client.generate_response(
                system_prompt=self.system_prompt,
                user_message=message,
                conversation_history=recent_history,
                tools=llm_tools
            )

            # Process the response
            if response["choices"][0]["message"]["tool_calls"]:
                # Execute requested tools
                tool_calls = response["choices"][0]["message"]["tool_calls"]
                results = []

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    try:
                        result = await self.tool_executor.execute_tool(tool_name, tool_args)

                        # Format the result appropriately
                        if tool_name == "run_command":
                            formatted = self._format_command_result(result, tool_args.get("command", ""))
                        elif tool_name == "read_file":
                            formatted = self._format_file_result(result, tool_args.get("file_path", ""))
                        elif tool_name == "write_file":
                            formatted = self._format_write_result(result, tool_args.get("file_path", ""))
                        elif tool_name == "list_directory":
                            formatted = self._format_ls_result(result, tool_args.get("directory", ""))
                        elif tool_name == "read_logs":
                            formatted = self._format_logs_result(result, tool_args.get("file_path", ""))
                        else:
                            # MCP tools
                            formatted = f"Tool '{tool_name}' executed successfully:\n{json.dumps(result, indent=2, ensure_ascii=False)}"

                        results.append(formatted)

                    except Exception as e:
                        results.append(f"Error executing {tool_name}: {str(e)}")

                # Combine tool results with LLM's explanation
                if response["choices"][0]["message"]["content"]:
                    explanation = response["choices"][0]["message"]["content"]
                    combined_result = f"{explanation}\n\n" + "\n\n".join(results)
                else:
                    combined_result = "\n\n".join(results)

                return combined_result

            else:
                # No tool calls, return LLM's direct response
                return response["choices"][0]["message"]["content"] or "I understand your request but don't need to use any tools for this."

        except Exception as e:
            logger.error(f"Error in LLM processing: {e}")
            return f"I encountered an error processing your request: {str(e)}. I'll try a simpler approach."

    async def _handle_simple_command(self, message: str) -> str:
        """Handle simple commands using basic parsing (fallback)."""
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
- logs /var/log/syslog

Or just ask me naturally: "Show me what's in my home directory" or "Find all Python files"""

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
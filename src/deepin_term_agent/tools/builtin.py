"""Built-in tools for the terminal agent."""

import asyncio
import os
import subprocess
import json
from typing import Any, Dict, List, Optional
import aiofiles
from pathlib import Path


class CommandRunner:
    """Tool for running shell commands."""
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Directory to run command in (optional)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds (default: 30)",
                    "default": 30
                }
            },
            "required": ["command"]
        }
    
    @staticmethod
    async def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command."""
        command = arguments["command"]
        working_dir = arguments.get("working_directory", os.getcwd())
        timeout = arguments.get("timeout", 30)
        
        try:
            # Change to specified directory if provided
            original_cwd = os.getcwd()
            if working_dir and os.path.exists(working_dir):
                os.chdir(working_dir)
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "command": command
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
        finally:
            # Restore original directory
            os.chdir(original_cwd)


class FileReader:
    """Tool for reading files."""
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: 1000)",
                    "default": 1000
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["file_path"]
        }
    
    @staticmethod
    async def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file's contents."""
        file_path = arguments["file_path"]
        max_lines = arguments.get("max_lines", 1000)
        encoding = arguments.get("encoding", "utf-8")
        
        try:
            path = Path(file_path).expanduser().resolve()
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            if not path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {file_path}"
                }
            
            async with aiofiles.open(path, 'r', encoding=encoding) as f:
                lines = []
                for i, line in enumerate(await f.readlines()):
                    if i >= max_lines:
                        lines.append(f"... (truncated at {max_lines} lines)")
                        break
                    lines.append(line.rstrip())
            
            return {
                "success": True,
                "content": "\n".join(lines),
                "file_path": str(path),
                "lines": len(lines),
                "size": path.stat().st_size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class FileWriter:
    """Tool for writing files."""
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "create_directories": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist",
                    "default": True
                },
                "append": {
                    "type": "boolean",
                    "description": "Append to file instead of overwriting",
                    "default": False
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["file_path", "content"]
        }
    
    @staticmethod
    async def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to a file."""
        file_path = arguments["file_path"]
        content = arguments["content"]
        create_dirs = arguments.get("create_directories", True)
        append = arguments.get("append", False)
        encoding = arguments.get("encoding", "utf-8")
        
        try:
            path = Path(file_path).expanduser().resolve()
            
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'a' if append else 'w'
            async with aiofiles.open(path, mode, encoding=encoding) as f:
                await f.write(content)
            
            return {
                "success": True,
                "file_path": str(path),
                "size": path.stat().st_size,
                "mode": "append" if append else "write"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class LogReader:
    """Tool for reading log files."""
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the log file"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of lines to read from end (default: 100)",
                    "default": 100
                },
                "follow": {
                    "type": "boolean",
                    "description": "Follow the log file (tail -f behavior)",
                    "default": False
                },
                "pattern": {
                    "type": "string",
                    "description": "Filter lines matching this pattern (regex)"
                }
            },
            "required": ["file_path"]
        }
    
    @staticmethod
    async def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Read log file contents."""
        file_path = arguments["file_path"]
        lines = arguments.get("lines", 100)
        follow = arguments.get("follow", False)
        pattern = arguments.get("pattern")
        
        try:
            path = Path(file_path).expanduser().resolve()
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Log file not found: {file_path}"
                }
            
            if follow:
                # For now, just return last N lines instead of tail -f
                # In a real implementation, this would stream updates
                pass
            
            # Read last N lines
            result = subprocess.run(
                ["tail", "-n", str(lines), str(path)],
                capture_output=True,
                text=True
            )
            
            content = result.stdout
            if pattern:
                import re
                regex = re.compile(pattern)
                content = "\n".join(
                    line for line in content.splitlines() 
                    if regex.search(line)
                )
            
            return {
                "success": True,
                "content": content,
                "file_path": str(path),
                "lines": len(content.splitlines())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class DirectoryLister:
    """Tool for listing directory contents."""
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to list (default: current directory)"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List recursively",
                    "default": False
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Show hidden files",
                    "default": False
                }
            }
        }
    
    @staticmethod
    async def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents."""
        directory = arguments.get("directory", ".")
        recursive = arguments.get("recursive", False)
        show_hidden = arguments.get("show_hidden", False)
        
        try:
            path = Path(directory).expanduser().resolve()
            
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}"
                }
            
            if not path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {directory}"
                }
            
            items = []
            if recursive:
                for item in path.rglob("*"):
                    if not show_hidden and item.name.startswith("."):
                        continue
                    items.append({
                        "name": str(item.relative_to(path)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                        "modified": item.stat().st_mtime
                    })
            else:
                for item in path.iterdir():
                    if not show_hidden and item.name.startswith("."):
                        continue
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                        "modified": item.stat().st_mtime
                    })
            
            return {
                "success": True,
                "directory": str(path),
                "items": items,
                "total": len(items)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Registry of built-in tools
BUILTIN_TOOLS = {
    "run_command": {
        "name": "run_command",
        "description": "Execute shell commands",
        "schema": CommandRunner.get_schema(),
        "execute": CommandRunner.execute
    },
    "read_file": {
        "name": "read_file",
        "description": "Read file contents",
        "schema": FileReader.get_schema(),
        "execute": FileReader.execute
    },
    "write_file": {
        "name": "write_file",
        "description": "Write content to files",
        "schema": FileWriter.get_schema(),
        "execute": FileWriter.execute
    },
    "read_logs": {
        "name": "read_logs",
        "description": "Read log files with filtering",
        "schema": LogReader.get_schema(),
        "execute": LogReader.execute
    },
    "list_directory": {
        "name": "list_directory",
        "description": "List directory contents",
        "schema": DirectoryLister.get_schema(),
        "execute": DirectoryLister.execute
    }
}
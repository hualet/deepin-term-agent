# Deepin Terminal Agent

An AI-powered terminal agent with TUI interface that uses the MCP (Model Context Protocol) to provide intelligent tool access. The agent ships with built-in tools for file operations, command execution, and log analysis.

## Features

- **TUI Interface**: Rich terminal interface built with Textual
- **MCP Protocol Support**: Connect to MCP servers for extended tool capabilities
- **Built-in Tools**: 
  - Command execution (`run_command`)
  - File reading (`read_file`)
  - File writing (`write_file`)
  - Log file analysis (`read_logs`)
  - Directory listing (`list_directory`)
- **Configuration Management**: Easy setup and management of MCP servers
- **Async Support**: Full async/await support for responsive operation
- **Extensible**: Easy to add new MCP servers and tools

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd deepin-term-agent

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### Initialize Configuration

```bash
# Create initial configuration
term-agent init-config

# Add MCP servers (optional)
term-agent add-server filesystem ws://localhost:8080
term-agent add-server git ws://localhost:8081
```

### Start the TUI

```bash
# Start the terminal agent interface
term-agent start
```

### Headless Mode

```bash
# Run a single command in headless mode
term-agent run --command "run ls -la /tmp"
```

## Usage

### TUI Interface

Once started, the TUI provides:
- **Chat area**: Main interaction with the agent
- **Tools panel**: View available tools
- **Logs tab**: View application logs
- **Keyboard shortcuts**:
  - `Ctrl+C`: Quit
  - `Ctrl+T`: Toggle tools panel
  - `Ctrl+L`: Clear chat
  - `Ctrl+R`: Refresh tools

### Command Examples

```bash
# Run shell commands
run ls -la /tmp
run ps aux | grep python

# Read files
read /etc/hosts
read ~/.bashrc --max-lines 50

# Write files
write /tmp/test.txt
Hello World!
This is a test file.

# List directories
ls /var/log
ls --recursive /home

# Read logs
logs /var/log/syslog --lines 100
logs /var/log/nginx/access.log --pattern "404"
```

## Configuration

Configuration is stored in `~/.config/deepin-term-agent/config.json`

### MCP Server Configuration

```json
{
  "mcp_servers": {
    "filesystem": {
      "url": "ws://localhost:8080",
      "enabled": true
    },
    "git": {
      "url": "ws://localhost:8081",
      "enabled": false
    }
  }
}
```

### CLI Commands for Configuration

```bash
# List configured servers
term-agent list-servers

# Add a new server
term-agent add-server my-server ws://localhost:9000

# Disable a server
term-agent add-server my-server ws://localhost:9000 --disable

# Remove a server
term-agent remove-server my-server
```

## Development

### Project Structure

```
src/deepin_term_agent/
├── agent/           # Main agent logic
├── config/          # Configuration management
├── mcp/             # MCP protocol client
├── tools/           # Built-in tools
├── tui/             # TUI interface
└── main.py          # CLI entry point
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/deepin_term_agent
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
ruff check src/
```

## Architecture

### Components

1. **TerminalAgent**: Main agent class that processes user messages
2. **ToolExecutor**: Manages both built-in and MCP tools
3. **MCPClient**: Handles MCP protocol communication
4. **AgentApp**: Textual TUI interface
5. **ConfigManager**: Configuration management

### Data Flow

1. User input → TUI → TerminalAgent
2. TerminalAgent → Tool selection → ToolExecutor
3. ToolExecutor → Built-in tool or MCP client → Execute
4. Results → TerminalAgent → Format → TUI display

## Extending

### Adding New Built-in Tools

Create a new tool in `src/deepin_term_agent/tools/builtin.py`:

```python
class MyCustomTool:
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"}
            },
            "required": ["param1"]
        }
    
    @staticmethod
    async def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Tool implementation
        return {"success": True, "result": "..."}

# Add to BUILTIN_TOOLS
BUILTIN_TOOLS["my_tool"] = {
    "name": "my_tool",
    "description": "My custom tool",
    "schema": MyCustomTool.get_schema(),
    "execute": MyCustomTool.execute
}
```

### Adding MCP Servers

Any MCP-compatible server can be added by updating the configuration:

```json
{
  "mcp_servers": {
    "my_server": {
      "url": "ws://my-server:8080",
      "enabled": true
    }
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

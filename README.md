# Deepin Terminal Agent

An AI-powered terminal agent with TUI interface that uses Moonshot K2 AI and the MCP (Model Context Protocol) to provide intelligent terminal assistance. The agent ships with built-in tools for file operations, command execution, and log analysis, enhanced by advanced AI capabilities.

## Features

- **🤖 AI-Powered**: Uses Moonshot K2 AI for intelligent command interpretation and tool selection
- **🎯 Natural Language**: Ask questions naturally without memorizing command syntax
- **🔧 TUI Interface**: Rich terminal interface built with Textual
- **🔄 MCP Protocol Support**: Connect to MCP servers for extended tool capabilities
- **📦 Built-in Tools**: 
  - Command execution (`run_command`)
  - File reading (`read_file`)
  - File writing (`write_file`)
  - Log file analysis (`read_logs`)
  - Directory listing (`list_directory`)
- **⚙️ Configuration Management**: Easy setup and management of MCP servers and AI settings
- **⚡ Async Support**: Full async/await support for responsive operation
- **🔌 Extensible**: Easy to add new MCP servers and tools

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

### AI Configuration (Recommended)

```bash
# Set up Moonshot K2 AI (interactive)
python setup_llm.py

# Or manually set environment variable
export MOONSHOT_API_KEY="your-api-key-here"
```

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

### AI-Powered Usage (Recommended)

With Moonshot K2 AI configured, you can use natural language:

```bash
# Natural language examples
"Show me what's in my home directory"
"Find all Python files in the current directory"
"Check the system logs for any errors in the last hour"
"Create a backup of my .bashrc file"
"What's taking up space in /var/log?"

# The AI will intelligently select and use appropriate tools
```

### Traditional Command Usage

You can also use traditional command syntax:

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
  },
  "llm": {
    "provider": "moonshot",
    "api_key": "your-api-key-here",
    "model": "k2",
    "temperature": 0.1,
    "max_tokens": 4000,
    "base_url": "https://api.moonshot.cn/v1"
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

1. **TerminalAgent**: Main agent class that processes user messages with AI intelligence
2. **ToolExecutor**: Manages both built-in and MCP tools
3. **MCPClient**: Handles MCP protocol communication
4. **MoonshotClient**: AI client for K2 LLM integration
5. **AgentApp**: Textual TUI interface
6. **ConfigManager**: Configuration management for both MCP and AI settings

### Data Flow

**AI-Powered Mode:**
1. User input → TUI → TerminalAgent
2. TerminalAgent → MoonshotClient (LLM) → Tool selection → ToolExecutor
3. ToolExecutor → Built-in tool or MCP client → Execute
4. Results → TerminalAgent → AI formatting → TUI display

**Fallback Mode:**
1. User input → TUI → TerminalAgent
2. TerminalAgent → Simple command parsing → ToolExecutor
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

## AI Features Deep Dive

### Natural Language Processing

The AI understands context and intent, allowing for complex requests:

```bash
# Complex operations made simple
"I need to find all files modified in the last hour that contain 'error' in their name"
"Show me a summary of the system logs, focusing on any warnings or errors"
"Create a Python script that monitors disk usage and alerts when above 80%"
```

### Context Awareness

- Maintains conversation history for context-aware responses
- Remembers previous commands and results
- Provides intelligent suggestions based on current directory and system state

### Safety Features

- AI evaluates command safety before execution
- Provides warnings for potentially dangerous operations
- Suggests safer alternatives when appropriate

## Troubleshooting

### AI Configuration Issues

**Problem**: "No Moonshot API key found"
```bash
# Solution 1: Interactive setup
python setup_llm.py

# Solution 2: Environment variable
export MOONSHOT_API_KEY="your-key-here"

# Solution 3: Manual config edit
# Edit ~/.config/deepin-term-agent/config.json
```

**Problem**: AI responses seem slow
- Check your internet connection to Moonshot API
- Consider reducing max_tokens in configuration
- Use environment variable for faster startup: `export MOONSHOT_API_KEY=...`

**Problem**: Fallback to simple commands
- Verify API key is valid (check Moonshot dashboard)
- Ensure base_url is correct (default: https://api.moonshot.cn/v1)
- Check logs for detailed error messages

### Performance Optimization

For better performance with large directories or files:
```json
{
  "llm": {
    "max_tokens": 2000,
    "temperature": 0.1,
    "model": "k2"
  }
}
```

## Contributing

### AI Development Guidelines

When contributing AI-related features:

1. **Test with real prompts**: Use diverse natural language inputs
2. **Handle edge cases**: Consider malformed requests, large outputs, timeouts
3. **Maintain fallback**: Always provide graceful fallback to simple parsing
4. **Security first**: AI should never execute obviously dangerous commands
5. **User experience**: Provide clear explanations of AI decisions

### Development Setup for AI Features

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Set up test API key
export MOONSHOT_API_KEY="test-key"

# Run AI-specific tests
pytest tests/test_llm_features.py

# Test natural language processing
python -m deepin_term_agent.cli.interactive --test-mode
```

## License

MIT License - see LICENSE file for details.

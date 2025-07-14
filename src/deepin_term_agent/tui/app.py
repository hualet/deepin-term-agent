"""Main TUI application for the terminal agent."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Input,
    RichLog,
    Tree,
    TabbedContent,
    TabPane,
    Static,
)
from textual.binding import Binding

from ..agent.agent import TerminalAgent
from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class AgentApp(App):
    """Main TUI application for the terminal agent."""
    
    CSS = """
    .tool-tree {
        width: 30%;
        dock: left;
    }
    
    .chat-area {
        width: 70%;
    }
    
    .input-area {
        height: 3;
        dock: bottom;
    }
    
    Log {
        height: 1fr;
    }
    
    #status {
        height: 1;
        dock: bottom;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+t", "toggle_tools", "Toggle Tools"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
        Binding("ctrl+r", "refresh_tools", "Refresh Tools"),
    ]
    
    def __init__(self):
        super().__init__()
        self.agent = TerminalAgent()
        self.config_manager = ConfigManager()
        self.current_tools: List[Dict[str, Any]] = []
        
    async def on_mount(self) -> None:
        """Initialize the application."""
        await self.agent.initialize()
        await self.refresh_tools()
        
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        
        with Horizontal():
            with Vertical(classes="tool-tree"):
                yield Static("Available Tools", id="tool-header")
                yield Tree("Tools", id="tool-tree")
                
            with Vertical(classes="chat-area"):
                with TabbedContent():
                    with TabPane("Chat"):
                        yield RichLog(id="chat-log", wrap=True, highlight=True)
                    with TabPane("Logs"):
                        yield RichLog(id="log-view", wrap=True)
                        
        with Horizontal(classes="input-area"):
            yield Input(placeholder="Type your message...", id="message-input")
            
        yield Static("Ready", id="status")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if not event.value.strip():
            return
            
        input_widget = self.query_one("#message-input", Input)
        chat_log = self.query_one("#chat-log", RichLog)
        
        # Clear input
        user_message = event.value
        input_widget.value = ""
        
        # Add user message to chat
        chat_log.write(f"[bold blue]You:[/bold blue] {user_message}")
        
        # Process message with agent
        try:
            response = await self.agent.process_message(user_message)
            chat_log.write(f"[bold green]Agent:[/bold green] {response}")
        except Exception as e:
            chat_log.write(f"[bold red]Error:[/bold red] {str(e)}")
            logger.exception("Error processing message")

    async def action_toggle_tools(self) -> None:
        """Toggle the tools panel visibility."""
        tool_tree = self.query_one(".tool-tree")
        if tool_tree.styles.width.value == 0:
            tool_tree.styles.width = "30%"
        else:
            tool_tree.styles.width = 0

    async def action_clear_chat(self) -> None:
        """Clear the chat log."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()

    async def action_refresh_tools(self) -> None:
        """Refresh the available tools list."""
        await self.refresh_tools()

    async def refresh_tools(self) -> None:
        """Refresh the tools list from MCP servers."""
        try:
            tools = await self.agent.list_tools()
            self.current_tools = tools
            
            tool_tree = self.query_one("#tool-tree", Tree)
            tool_tree.clear()
            
            for tool in tools:
                tool_tree.root.add_leaf(f"{tool['name']}: {tool['description']}")
                
            status = self.query_one("#status", Static)
            status.update(f"Loaded {len(tools)} tools")
            
        except Exception as e:
            logger.exception("Error refreshing tools")
            status = self.query_one("#status", Static)
            status.update(f"Error loading tools: {e}")

    def log_message(self, message: str, level: str = "INFO") -> None:
        """Log a message to the log view."""
        log_view = self.query_one("#log-view", RichLog)
        log_view.write(f"[{level}] {message}")

    async def on_unmount(self) -> None:
        """Cleanup when app closes."""
        await self.agent.cleanup()
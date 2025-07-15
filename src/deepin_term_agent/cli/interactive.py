"""Interactive CLI interface similar to Claude Code."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

PROMPT_AVAILABLE = False
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.shortcuts import CompleteStyle
    PROMPT_AVAILABLE = True
except ImportError:
    pass

from ..agent.agent import TerminalAgent
from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


if PROMPT_AVAILABLE:
    class ToolCompleter(Completer):
        """Auto-completion for available tools and commands."""
        
        def __init__(self, tools: List[Dict[str, Any]]):
            self.tools = tools
            self.commands = [
                "run", "read", "write", "ls", "logs", "help", "tools", "exit", "quit"
            ]
        
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            
            # Complete commands
            if " " not in text:
                for command in self.commands:
                    if command.startswith(text.lower()):
                        yield Completion(command, start_position=-len(text))
            
            # Complete tool names
            elif text.startswith("run ") or text.startswith("read ") or text.startswith("write "):
                # File path completion could be added here
                pass


class InteractiveCLI:
    """Interactive CLI interface similar to Claude Code."""
    
    def __init__(self):
        self.console = Console()
        self.agent = TerminalAgent()
        self.config_manager = ConfigManager()
        self.current_tools: List[Dict[str, Any]] = []
        
        # Setup prompt session
        if PROMPT_AVAILABLE:
            history_file = Path.home() / ".deepin-term-agent" / "history"
            history_file.parent.mkdir(exist_ok=True)
            self.session = PromptSession(
                history=FileHistory(str(history_file)),
                auto_suggest=AutoSuggestFromHistory(),
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
    
    async def initialize(self):
        """Initialize the CLI."""
        self.console.print(Panel(
            "[bold green]Deepin Terminal Agent[/bold green]\n"
            "Type [cyan]help[/cyan] for available commands or [cyan]exit[/cyan] to quit.",
            title="Welcome",
            border_style="green"
        ))
        
        await self.agent.initialize()
        self.current_tools = await self.agent.list_tools()
        
        if self.current_tools:
            self.console.print(f"[dim]Loaded {len(self.current_tools)} tools[/dim]")
    
    async def run(self):
        """Run the interactive CLI."""
        await self.initialize()
        
        try:
            while True:
                try:
                    if PROMPT_AVAILABLE:
                        # Use prompt_toolkit for rich interaction
                        user_input = await self._prompt_async()
                    else:
                        # Fallback to basic input
                        user_input = input("> ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ["exit", "quit", "q"]:
                        break
                    
                    await self._process_command(user_input)
                    
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                    continue
                except EOFError:
                    break
                    
        finally:
            await self.agent.cleanup()
    
    async def _prompt_async(self):
        """Async prompt with auto-completion."""
        completer = ToolCompleter(self.current_tools)
        
        try:
            return await self.session.prompt_async(
                "> ",
                completer=completer,
            )
        except KeyboardInterrupt:
            return ""
    
    async def _process_command(self, command: str):
        """Process a user command."""
        try:
            response = await self.agent.process_message(command)
            self._display_response(response)
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            logger.exception("Error processing command")
    
    def _display_response(self, response: str):
        """Display the response with rich formatting."""
        # Detect if response contains code blocks
        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    if part.strip():
                        self.console.print(Markdown(part))
                else:  # Code block
                    lines = part.split('\n', 1)
                    if len(lines) > 1:
                        lang = lines[0].strip()
                        code = lines[1]
                        syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                        self.console.print(Panel(syntax, title=f"Code ({lang})", border_style="blue"))
                    else:
                        self.console.print(Panel(part, title="Code", border_style="blue"))
        else:
            self.console.print(response)
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.agent.cleanup()


class SimpleCLI:
    """Simple CLI without prompt_toolkit for fallback."""
    
    def __init__(self):
        self.console = Console()
        self.agent = TerminalAgent()
    
    async def run(self):
        """Run the simple CLI."""
        await self.agent.initialize()
        
        try:
            while True:
                try:
                    user_input = input("> ").strip()
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ["exit", "quit", "q"]:
                        break
                    
                    response = await self.agent.process_message(user_input)
                    self.console.print(response)
                    
                except KeyboardInterrupt:
                    print("\nUse 'exit' to quit")
                    continue
                except EOFError:
                    break
                    
        finally:
            await self.agent.cleanup()


async def run_interactive():
    """Run the interactive CLI."""
    if PROMPT_AVAILABLE:
        cli = InteractiveCLI()
    else:
        cli = SimpleCLI()
    
    await cli.run()
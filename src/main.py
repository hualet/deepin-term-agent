"""Main entry point for the terminal agent."""

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from deepin_term_agent.config.manager import ConfigManager

console = Console()


def setup_logging(level: str = "INFO", log_file: str = None):
    """Setup logging configuration."""
    handlers = []

    # Console handler with rich formatting
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False
    )
    console_handler.setLevel(getattr(logging, level.upper()))
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        format="%(message)s",
        datefmt="[%X]"
    )


@click.group(invoke_without_command=True)
@click.option('--config-dir', type=click.Path(), help='Configuration directory')
@click.pass_context
def cli(ctx, config_dir):
    """Deepin Terminal Agent - AI-powered terminal with MCP protocol support."""
    ctx.ensure_object(dict)

    config_manager = ConfigManager(config_dir)
    ctx.obj['config_manager'] = config_manager

    # Setup logging based on config
    log_config = config_manager.get_logging_config()
    setup_logging(
        level=log_config.get('level', 'INFO'),
        log_file=log_config.get('file')
    )

    # If no command provided, run the start command by default
    if ctx.invoked_subcommand is None:
        ctx.invoke(start)


@cli.command()
@click.pass_context
def start(ctx):
    """Start the interactive CLI (like Claude Code)."""
    from deepin_term_agent.cli.interactive import run_interactive

    console.print("[bold green]Starting Deepin Terminal Agent CLI...[/bold green]")

    try:
        asyncio.run(run_interactive())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.argument('url')
@click.option('--disable', is_flag=True, help='Disable the server')
@click.pass_context
def add_server(ctx, name, url, disable):
    """Add an MCP server configuration."""
    config_manager = ctx.obj['config_manager']

    success = config_manager.add_mcp_server(name, url, not disable)
    if success:
        console.print(f"[green]Added MCP server: {name} ({url})[/green]")
    else:
        console.print(f"[red]Failed to add MCP server: {name}[/red]")


@cli.command()
@click.argument('name')
@click.pass_context
def remove_server(ctx, name):
    """Remove an MCP server configuration."""
    config_manager = ctx.obj['config_manager']

    success = config_manager.remove_mcp_server(name)
    if success:
        console.print(f"[green]Removed MCP server: {name}[/green]")
    else:
        console.print(f"[red]MCP server not found: {name}[/red]")


@cli.command()
@click.pass_context
def list_servers(ctx):
    """List all configured MCP servers."""
    config_manager = ctx.obj['config_manager']

    servers = config_manager.get_mcp_servers()
    if not servers:
        console.print("[yellow]No MCP servers configured[/yellow]")
        return

    console.print("[bold]Configured MCP Servers:[/bold]")
    for name, config in servers.items():
        status = "[green]enabled[/green]" if config.get("enabled", True) else "[red]disabled[/red]"
        console.print(f"  {name}: {config['url']} ({status})")


@cli.command()
@click.pass_context
def init_config(ctx):
    """Initialize configuration with sample settings."""
    config_manager = ctx.obj['config_manager']

    config_manager.create_sample_config()
    console.print(f"[green]Configuration directory: {config_manager.get_config_dir()}[/green]")


@cli.command()
@click.option('--command', help='Command to run in headless mode')
@click.pass_context
def run(ctx, command):
    """Run in headless mode (execute a single command)."""
    from deepin_term_agent.agent.agent import TerminalAgent

    if not command:
        console.print("[red]Error: --command is required for headless mode[/red]")
        sys.exit(1)

    async def _run_command():
        agent = TerminalAgent()
        await agent.initialize()

        try:
            response = await agent.process_message(command)
            console.print(response)
        finally:
            await agent.cleanup()

    asyncio.run(_run_command())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
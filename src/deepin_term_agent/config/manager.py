"""Configuration management for the terminal agent."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages configuration for the terminal agent."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.expanduser("~/.config/deepin-term-agent")
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self.mcp_dir = self.config_dir / "mcp-servers"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        default_config = {
            "mcp_servers": {},
            "logging": {
                "level": "INFO",
                "file": str(self.config_dir / "agent.log")
            },
            "ui": {
                "theme": "dark",
                "show_tool_output": True,
                "auto_scroll": True
            },
            "tools": {
                "builtin": {
                    "enabled": True
                }
            }
        }
        
        if not self.config_file.exists():
            # Create default config
            self.save_config(default_config)
            return default_config
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Merge with default config to ensure all keys exist
            merged_config = default_config.copy()
            merged_config.update(config)
            return merged_config
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return default_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False
    
    def add_mcp_server(self, name: str, url: str, enabled: bool = True) -> bool:
        """Add an MCP server configuration."""
        config = self.load_config()
        
        if "mcp_servers" not in config:
            config["mcp_servers"] = {}
        
        config["mcp_servers"][name] = {
            "url": url,
            "enabled": enabled
        }
        
        return self.save_config(config)
    
    def remove_mcp_server(self, name: str) -> bool:
        """Remove an MCP server configuration."""
        config = self.load_config()
        
        if "mcp_servers" in config and name in config["mcp_servers"]:
            del config["mcp_servers"][name]
            return self.save_config(config)
        
        return False
    
    def update_mcp_server(self, name: str, url: Optional[str] = None, 
                         enabled: Optional[bool] = None) -> bool:
        """Update an MCP server configuration."""
        config = self.load_config()
        
        if "mcp_servers" not in config or name not in config["mcp_servers"]:
            return False
        
        if url is not None:
            config["mcp_servers"][name]["url"] = url
        
        if enabled is not None:
            config["mcp_servers"][name]["enabled"] = enabled
        
        return self.save_config(config)
    
    def get_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get all MCP server configurations."""
        config = self.load_config()
        return config.get("mcp_servers", {})
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        config = self.load_config()
        return config.get("tools", {}).get(tool_name, {})
    
    def set_tool_config(self, tool_name: str, config: Dict[str, Any]) -> bool:
        """Set configuration for a specific tool."""
        main_config = self.load_config()
        
        if "tools" not in main_config:
            main_config["tools"] = {}
        
        main_config["tools"][tool_name] = config
        return self.save_config(main_config)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration."""
        config = self.load_config()
        return config.get("ui", {})
    
    def set_ui_config(self, config: Dict[str, Any]) -> bool:
        """Set UI configuration."""
        main_config = self.load_config()
        main_config["ui"] = config
        return self.save_config(main_config)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        config = self.load_config()
        return config.get("logging", {})
    
    def set_logging_config(self, config: Dict[str, Any]) -> bool:
        """Set logging configuration."""
        main_config = self.load_config()
        main_config["logging"] = config
        return self.save_config(main_config)
    
    def create_sample_config(self) -> None:
        """Create a sample configuration file."""
        sample_config = {
            "mcp_servers": {
                "filesystem": {
                    "url": "ws://localhost:8080",
                    "enabled": True
                },
                "git": {
                    "url": "ws://localhost:8081",
                    "enabled": False
                }
            },
            "logging": {
                "level": "INFO",
                "file": str(self.config_dir / "agent.log")
            },
            "ui": {
                "theme": "dark",
                "show_tool_output": True,
                "auto_scroll": True
            },
            "tools": {
                "builtin": {
                    "enabled": True
                },
                "run_command": {
                    "default_timeout": 30,
                    "max_output_size": 1024 * 1024  # 1MB
                }
            }
        }
        
        sample_file = self.config_dir / "config.sample.json"
        with open(sample_file, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        print(f"Sample configuration created at: {sample_file}")
    
    def get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self.config_dir
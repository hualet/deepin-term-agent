#!/usr/bin/env python3
"""Setup script for configuring Moonshot K2 API integration."""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deepin_term_agent.config.manager import ConfigManager


def setup_moonshot_api():
    """Interactive setup for Moonshot API configuration."""
    print("🤖 Moonshot K2 AI Setup")
    print("=" * 50)
    print()
    print("This will help you configure Moonshot K2 API for intelligent terminal assistance.")
    print()
    
    # Check if API key is already set
    config_manager = ConfigManager()
    config = config_manager.load_config()
    llm_config = config.get("llm", {})
    
    current_key = llm_config.get("api_key") or os.getenv("MOONSHOT_API_KEY")
    if current_key:
        masked_key = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "***"
        print(f"Current API key: {masked_key}")
        print()
    
    # Get new API key
    print("To get your Moonshot API key:")
    print("1. Go to https://platform.moonshot.cn/")
    print("2. Create an account or log in")
    print("3. Navigate to API Keys section")
    print("4. Create a new API key")
    print()
    
    api_key = input("Enter your Moonshot API key: ").strip()
    if not api_key:
        print("❌ No API key provided. Setup cancelled.")
        return False
    
    # Save configuration
    llm_config.update({
        "provider": "moonshot",
        "api_key": api_key,
        "model": "k2",
        "temperature": 0.1,
        "max_tokens": 4000,
        "base_url": "https://api.moonshot.cn/v1"
    })
    
    config["llm"] = llm_config
    
    if config_manager.save_config(config):
        print("✅ Moonshot K2 API configured successfully!")
        print()
        print("You can also set the API key as an environment variable:")
        print('export MOONSHOT_API_KEY="your-key-here"')
        print()
        print("The agent will now use Moonshot K2 AI for intelligent assistance.")
        return True
    else:
        print("❌ Failed to save configuration.")
        return False


def main():
    """Main setup function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python setup_llm.py")
        print("Interactive setup for Moonshot K2 API configuration")
        return
    
    try:
        setup_moonshot_api()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
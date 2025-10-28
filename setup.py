#!/usr/bin/env python3
"""
Install and setup script for MCP Guidelines Server with Claude Code
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_mcp_server():
    """Install and configure the MCP Guidelines Server for Claude Code."""
    
    print("=== MCP Guidelines Server Setup for Claude Code ===\n")
    
    # 1. Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print("✅ Python version OK")
    
    # 2. Install dependencies
    print("\n📦 Installing dependencies...")
    packages = ["mcp", "tiktoken"]
    for package in packages:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            print(f"   Please run: pip install {package}")
            return False
    
    # 3. Create guidelines directory
    project_path = Path.cwd()
    guidelines_dir = project_path / ".claude"
    guidelines_dir.mkdir(exist_ok=True)
    print(f"\n✅ Created guidelines directory: {guidelines_dir}")
    
    # 4. Check for server file
    server_file = project_path / "mcp_guidelines_server.py"
    if not server_file.exists():
        print(f"❌ Server file not found: {server_file}")
        print("   Please ensure mcp_guidelines_server.py is in the current directory")
        return False
    print(f"✅ Server file found: {server_file}")
    
    # 5. Add the server to Claude Code
    print("\n🔧 Adding server to Claude Code...\n")
    
    # Build the claude mcp add command
    cmd = [
        "claude", "mcp", "add", 
        "guidelines",  # server name
        "--scope", "local",  # project-specific
        "--",  # separator
        sys.executable,  # python executable
        str(server_file),  # server script
        str(project_path)  # project path argument
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=5, shell=True)
        print("✅ Server added to Claude Code successfully!")
        if result.stdout:
            print(result.stdout)
    except FileNotFoundError:
        print("❌ Claude Code CLI not found")
        print("\nPlease install Claude Code first:")
        print("https://docs.claude.com/en/docs/claude-code/getting-started")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to add server: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        print("\nTry manually adding the server:")
        print(f"claude mcp add guidelines -- {sys.executable} {server_file} {project_path}")
        return False
    
    # 6. Create example guidelines if they don't exist
    example_guidelines = {
        "critical_git_workflow.md": """# Git Workflow Guidelines

## CRITICAL: Branch Strategy
- Always create feature branches from `main`
- Never commit directly to `main` or `develop`
- Branch naming: `feature/description`, `fix/description`, `docs/description`

## Commit Messages
- Use conventional commits: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
""",
        "important_code_style.md": """# Code Style Guidelines

## Python Style
- Use Black formatter with line length 88
- Type hints for all function parameters and returns
- Docstrings for all public functions (Google style)

## Testing Requirements
- Minimum 80% code coverage
- Unit tests for all business logic
"""
    }
    
    for filename, content in example_guidelines.items():
        file_path = guidelines_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"✅ Created example guideline: {filename}")
    
    # 7. Success message and instructions
    print("\n" + "="*50)
    print("✨ Setup Complete!\n")
    print("How to use the MCP Guidelines Server:")
    print("-" * 40)
    print("1. The server is now registered with Claude Code")
    print("2. Use @ in your prompts to access resources:")
    print("   - @guidelines:git://status - Current git status")
    print("   - @guidelines:context://active - Active guidelines")
    print("\n3. Use / commands for tools:")
    print("   - /mcp__guidelines__add_guideline - Add new guidelines")
    print("   - /mcp__guidelines__force_refresh - Refresh git status")
    print("\n4. Add more guidelines as .md files in .claude/ directory")
    print("\n💡 Tips:")
    print("- High-priority items (priority 8-10) repeat more frequently")
    print("- Files named 'critical_*' get priority 10 (always visible)")
    print("- Files named 'important_*' get priority 8")
    
    return True


def check_claude_code():
    """Check if Claude Code CLI is available."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True  # Windows may need shell=True to find claude in PATH
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Debug: Check failed with error: {e}")
        return False


if __name__ == "__main__":
    print("Checking for Claude Code CLI...")
    if not check_claude_code():
        print("\n⚠️  Claude Code CLI not found!")
        print("\nPlease install Claude Code first:")
        print("1. Visit: https://docs.claude.com/en/docs/claude-code/getting-started")
        print("2. Install the Claude Code CLI")
        print("3. Run this setup script again")
        sys.exit(1)
    
    print("✅ Claude Code CLI found\n")
    
    success = setup_mcp_server()
    sys.exit(0 if success else 1)
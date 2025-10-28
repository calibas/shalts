#!/usr/bin/env python3
"""
MCP Guidelines Server
Tracks git status, manages documentation, and repeats important context based on token usage.
"""

import asyncio
import json
import os
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict
import mcp.server
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent, CallToolResult
import tiktoken  # For token counting

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ContextItem:
    """Represents a piece of context with priority and token tracking."""
    id: str
    content: str
    priority: int  # 1-10, higher = more important
    category: str  # 'guideline', 'state', 'documentation'
    last_shown_at_token: int = 0
    repeat_after_tokens: int = 5000  # Default repeat interval
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class GitTracker:
    """Tracks git repository status."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive git status."""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "branch": self._get_current_branch(),
                "status": self._get_status_output(),
                "recent_commits": self._get_recent_commits(5),
                "uncommitted_changes": self._get_diff_stats(),
                "remotes": self._get_remotes(),
                "stash_count": self._get_stash_count()
            }
            return status
        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return {"error": str(e)}
    
    def _run_git_command(self, args: List[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"
    
    def _get_current_branch(self) -> str:
        return self._run_git_command(["branch", "--show-current"])
    
    def _get_status_output(self) -> str:
        return self._run_git_command(["status", "--short"])
    
    def _get_recent_commits(self, count: int) -> List[str]:
        output = self._run_git_command(
            ["log", f"-{count}", "--oneline", "--decorate"]
        )
        return output.split('\n') if output else []
    
    def _get_diff_stats(self) -> Dict[str, int]:
        staged = self._run_git_command(["diff", "--cached", "--numstat"])
        unstaged = self._run_git_command(["diff", "--numstat"])
        
        stats = {
            "staged_files": len(staged.split('\n')) if staged else 0,
            "unstaged_files": len(unstaged.split('\n')) if unstaged else 0
        }
        return stats
    
    def _get_remotes(self) -> List[str]:
        output = self._run_git_command(["remote", "-v"])
        return output.split('\n') if output else []
    
    def _get_stash_count(self) -> int:
        output = self._run_git_command(["stash", "list"])
        return len(output.split('\n')) if output else 0


class ContextManager:
    """Manages context items with token-based repetition."""
    
    def __init__(self, repeat_threshold: int = 5000):
        self.contexts: Dict[str, ContextItem] = {}
        self.token_counter = 0
        self.repeat_threshold = repeat_threshold
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")  # Claude uses similar tokenization
        
    def add_context(self, context: ContextItem) -> None:
        """Add or update a context item."""
        self.contexts[context.id] = context
        
    def remove_context(self, context_id: str) -> bool:
        """Remove a context item."""
        if context_id in self.contexts:
            del self.contexts[context_id]
            return True
        return False
    
    def get_active_contexts(self) -> List[ContextItem]:
        """Get contexts that should be shown based on token count."""
        active = []
        for context in self.contexts.values():
            tokens_since_shown = self.token_counter - context.last_shown_at_token
            if tokens_since_shown >= context.repeat_after_tokens:
                active.append(context)
                context.last_shown_at_token = self.token_counter
        
        # Always include high-priority items
        for context in self.contexts.values():
            if context.priority >= 8 and context not in active:
                active.append(context)
        
        # Sort by priority
        return sorted(active, key=lambda x: x.priority, reverse=True)
    
    def increment_tokens(self, text: str) -> None:
        """Increment token counter based on text."""
        tokens = len(self.tokenizer.encode(text))
        self.token_counter += tokens
        logger.info(f"Token counter: {self.token_counter} (+{tokens})")
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of all contexts."""
        return {
            "total_contexts": len(self.contexts),
            "current_token_count": self.token_counter,
            "contexts_by_category": self._group_by_category(),
            "next_repetitions": self._get_next_repetitions()
        }
    
    def _group_by_category(self) -> Dict[str, int]:
        groups = {}
        for context in self.contexts.values():
            groups[context.category] = groups.get(context.category, 0) + 1
        return groups
    
    def _get_next_repetitions(self) -> List[Dict[str, Any]]:
        """Get when contexts will next be repeated."""
        repetitions = []
        for context in self.contexts.values():
            tokens_until_repeat = (
                context.last_shown_at_token + 
                context.repeat_after_tokens - 
                self.token_counter
            )
            if tokens_until_repeat > 0:
                repetitions.append({
                    "id": context.id,
                    "tokens_until_repeat": tokens_until_repeat,
                    "priority": context.priority
                })
        return sorted(repetitions, key=lambda x: x['tokens_until_repeat'])


class GuidelinesServer:
    """Main MCP server for guidelines and context management."""
    
    def __init__(self, project_path: str = ".", guidelines_dir: str = ".claude"):
        self.project_path = Path(project_path).resolve()
        self.guidelines_dir = self.project_path / guidelines_dir
        self.guidelines_dir.mkdir(exist_ok=True)
        
        self.git_tracker = GitTracker(project_path)
        self.context_manager = ContextManager()
        self.server = Server("guidelines-server")
        
        # Load initial guidelines
        self._load_guidelines()
        
        # Set up MCP handlers
        self._setup_handlers()
        
        # Start background tasks
        asyncio.create_task(self._update_git_status_periodically())
    
    def _load_guidelines(self) -> None:
        """Load guidelines from the guidelines directory."""
        for file_path in self.guidelines_dir.glob("*.md"):
            content = file_path.read_text()
            context_id = f"guideline_{file_path.stem}"
            
            # Determine priority from filename or content
            priority = 5  # Default
            if "critical" in file_path.stem.lower():
                priority = 10
            elif "important" in file_path.stem.lower():
                priority = 8
                
            context = ContextItem(
                id=context_id,
                content=content,
                priority=priority,
                category="guideline",
                repeat_after_tokens=3000 if priority >= 8 else 5000
            )
            self.context_manager.add_context(context)
            logger.info(f"Loaded guideline: {file_path.name}")
    
    def _setup_handlers(self) -> None:
        """Set up MCP server handlers."""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List all available resources."""
            resources = []
            
            # Add git status resource
            resources.append(Resource(
                uri="git://status",
                name="Current Git Status",
                mimeType="application/json"
            ))
            
            # Add guideline resources
            for context_id, context in self.context_manager.contexts.items():
                resources.append(Resource(
                    uri=f"context://{context_id}",
                    name=context_id.replace('_', ' ').title(),
                    mimeType="text/markdown"
                ))
            
            # Add active contexts resource (what should be shown now)
            resources.append(Resource(
                uri="context://active",
                name="Active Context Items",
                mimeType="text/markdown"
            ))
            
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> TextContent:
            """Read a specific resource."""
            if uri == "git://status":
                status = self.git_tracker.get_status()
                return TextContent(
                    text=json.dumps(status, indent=2),
                    mimeType="application/json"
                )
            
            elif uri == "context://active":
                active_contexts = self.context_manager.get_active_contexts()
                combined_text = "\n\n---\n\n".join([
                    f"# {ctx.id} (Priority: {ctx.priority})\n\n{ctx.content}"
                    for ctx in active_contexts
                ])
                return TextContent(
                    text=combined_text or "No active contexts to show currently.",
                    mimeType="text/markdown"
                )
            
            elif uri.startswith("context://"):
                context_id = uri.replace("context://", "")
                if context_id in self.context_manager.contexts:
                    context = self.context_manager.contexts[context_id]
                    return TextContent(
                        text=context.content,
                        mimeType="text/markdown"
                    )
            
            return TextContent(text="Resource not found", mimeType="text/plain")
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="add_guideline",
                    description="Add a new guideline or context item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "content": {"type": "string"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 10},
                            "category": {"type": "string", "enum": ["guideline", "state", "documentation"]},
                            "repeat_after_tokens": {"type": "integer"}
                        },
                        "required": ["id", "content"]
                    }
                ),
                Tool(
                    name="remove_guideline",
                    description="Remove a guideline or context item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"}
                        },
                        "required": ["id"]
                    }
                ),
                Tool(
                    name="track_tokens",
                    description="Track token usage for context repetition",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="get_context_summary",
                    description="Get summary of all contexts and repetition schedule",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="force_refresh",
                    description="Force refresh of git status and active contexts",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            if name == "add_guideline":
                context = ContextItem(
                    id=arguments["id"],
                    content=arguments["content"],
                    priority=arguments.get("priority", 5),
                    category=arguments.get("category", "guideline"),
                    repeat_after_tokens=arguments.get("repeat_after_tokens", 5000)
                )
                self.context_manager.add_context(context)
                
                # Optionally save to file
                if context.category == "guideline":
                    file_path = self.guidelines_dir / f"{context.id}.md"
                    file_path.write_text(context.content)
                
                return CallToolResult(
                    content=[TextContent(text=f"Added context: {context.id}")]
                )
            
            elif name == "remove_guideline":
                success = self.context_manager.remove_context(arguments["id"])
                return CallToolResult(
                    content=[TextContent(
                        text=f"{'Removed' if success else 'Failed to remove'} context: {arguments['id']}"
                    )]
                )
            
            elif name == "track_tokens":
                self.context_manager.increment_tokens(arguments["text"])
                return CallToolResult(
                    content=[TextContent(
                        text=f"Tracked {len(self.context_manager.tokenizer.encode(arguments['text']))} tokens"
                    )]
                )
            
            elif name == "get_context_summary":
                summary = self.context_manager.get_context_summary()
                return CallToolResult(
                    content=[TextContent(text=json.dumps(summary, indent=2))]
                )
            
            elif name == "force_refresh":
                # Update git status
                git_status = self.git_tracker.get_status()
                
                # Create/update git status context
                git_context = ContextItem(
                    id="git_status",
                    content=json.dumps(git_status, indent=2),
                    priority=6,
                    category="state",
                    repeat_after_tokens=2000
                )
                self.context_manager.add_context(git_context)
                
                return CallToolResult(
                    content=[TextContent(text="Refreshed git status and contexts")]
                )
            
            return CallToolResult(
                content=[TextContent(text=f"Unknown tool: {name}")]
            )
    
    async def _update_git_status_periodically(self) -> None:
        """Update git status every 30 seconds."""
        while True:
            await asyncio.sleep(30)
            try:
                git_status = self.git_tracker.get_status()
                git_context = ContextItem(
                    id="git_status",
                    content=json.dumps(git_status, indent=2),
                    priority=6,
                    category="state",
                    repeat_after_tokens=2000  # Show git status more frequently
                )
                self.context_manager.add_context(git_context)
                logger.info("Updated git status")
            except Exception as e:
                logger.error(f"Error updating git status: {e}")
    
    async def run(self) -> None:
        """Run the MCP server."""
        async with mcp.server.stdio_server() as (read_stream, write_stream):
            logger.info("Guidelines MCP Server started")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    import sys
    
    # Get project path from command line or use current directory
    project_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    server = GuidelinesServer(project_path)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
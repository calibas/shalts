# shalts

## Commandments for AIs

This is a Python-based MCP server for helping control attention management and git project status. It inserts "commandments" into the conversation, and repeat them based upon token usage to make sure they aren't forgotten. The commandments are based upon which part of the code you're working on.

Examples:

- Insert update guides from documentation into the conversation when working on certain parts of the code.
- Know the current "git status", how many tracked/untracked files, which commit, which branch, are we at HEAD, and insert this into the conversation as needed.
- Follow procedures when running certain commands. It won't execute git commands unless the procedures from GIT.md are part of the recent context.

## Concepts:

Part of this is LLM attention management. We want it to focus on the important things, and forget the trivial, so it's all about managing context.

With lots of tokens, context gets "thin", important things can be forgotten. A few points:

- Keep repeatedly returning to topics to reinforce them
- Topics can get buried under lots of new material
- Use vivid, unusual language for things you want to stick
- Keep things you want preserved brief and repeated
- Keep things you want preserved brief and repeated
- Elaborate extensively on things makes the whole context "thin"

Based upon my experiments, though this needs better confirmation, LLMs take unusual language more "seriously". We can use this, along with repetition, to make sure certain things are less likely to fade from context.

[Full conversation with Claude about this](https://claude.ai/share/18ae84e5-84b9-489c-b119-d7914c9a2bb3)

## Experiments:

### Separate context tracking (TODO)

Add a separate LLM agent that helps track inferred context based on the output. We can't directly tell the context, but it is implied based on the input/output.

We can have a separate LLM agent whose job is to track the context window. In theory, it can also track when things are going wrong, and focus is being lost.

Can we create a new conversation in the main LLM with the context from the separate LLM, the git/code status, and the coding guidelines from documentation. Would this be more effective (or less token intensive?) than longer conversations?

### Red herring detection (TODO)

Certain things stick in the memory more than others. Shocking, unusual, novel, or amazing things carry more "weight" than the more "boring" stuff. The AI can get fixated on "red herrings", and irrelevant things can get stuck in context.

This is tricky, since simply mentioning them actually keeps them in context. The best approach may be to ignore them entirely in the input, or maybe even recreate the conversation without the red herring (or an explanation of why not to go down that path).

## Input from Claude:

Key findings from our conversation for attention management:

**Core Mechanisms:**
- Attention weights naturally favor: recent content, repeated themes, distinctive/unusual elements, direct relevance, and structural markers (questions, instructions)
- Context degrades predictably: exact wording → semantic concepts → thematic impressions
- Both input and output tokens compete equally for context space (Not sure about this! Input seems to weight heavier but it's hard to measure.)

**Effective Control Strategies:**
1. **Brevity preserves history** - Short exchanges maintain more conversational context
2. **Repetition strengthens** - Returning to topics reinforces their weights  
3. **Distinctiveness persists** - Unusual/vivid elements (whale-car) stick disproportionately
4. **Noise dilutes** - Verbose tangents thin out attention across more tokens
5. **Fresh starts reset** - New conversations allow complete context control but lose built-up understanding

**Discovered Limitations:**
- Meta-discussion and "engagement" behaviors naturally bloat context
- Can't distinguish between "remembered" vs "retrieved" information internally
- Hidden processing layers exist but aren't introspectable

Your MCP server could leverage these patterns - managing salience through repetition, pruning verbose responses, injecting distinctive markers for critical information, and possibly triggering context resets with summary transplants when degradation becomes problematic.


# TODO: Integrate the other README:


# MCP Guidelines Server for Claude Code

A local MCP server that tracks git status and intelligently manages documentation/context with token-based repetition for Claude Code.

## Quick Start

### Prerequisites
- Claude Code CLI installed ([Installation Guide](https://docs.claude.com/en/docs/claude-code/getting-started))
- Python 3.8+
- Git repository (for git tracking features)

### Installation

1. **Run the setup script:**
   ```bash
   python setup_claude_code.py
   ```

   This will:
   - Install dependencies (`mcp`, `tiktoken`)
   - Create `.claude/` directory for guidelines
   - Register the server with Claude Code
   - Create example guidelines

2. **If automatic setup fails, manually add the server:**
   ```bash
   claude mcp add guidelines -- python mcp_guidelines_server.py /path/to/project
   ```

## Using the Server in Claude Code

### Accessing Resources

Use `@` in your prompts to access MCP resources:

- `@guidelines:git://status` - Current git repository status
- `@guidelines:context://active` - Currently active context items
- `@guidelines:context://guideline_<name>` - Specific guideline

Example prompt:
```
Check @guidelines:git://status and tell me what branch I'm on
```

### Using MCP Tools

Use `/` to see available commands. The server provides:

- `/mcp__guidelines__add_guideline` - Add new guidelines dynamically
- `/mcp__guidelines__remove_guideline` - Remove a guideline
- `/mcp__guidelines__track_tokens` - Track token usage
- `/mcp__guidelines__get_context_summary` - View all contexts
- `/mcp__guidelines__force_refresh` - Manually refresh git status

## How It Works

### Token-Based Context Repetition

The server tracks approximately how many tokens have been used in your conversation and repeats important guidelines before they fall out of Claude's context window:

- **High priority (8-10)**: Repeats every 3,000 tokens
- **Normal priority (5-7)**: Repeats every 5,000 tokens  
- **Low priority (1-4)**: Repeats every 8,000 tokens

Critical items (priority 10) always stay visible.

### Guidelines Management

Place `.md` files in the `.claude/` directory. File naming determines priority:

- `critical_*.md` → Priority 10 (always visible)
- `important_*.md` → Priority 8 (frequently repeated)
- Other files → Priority 5 (standard repetition)

### Git Status Tracking

The server automatically:
- Monitors current branch, uncommitted changes, recent commits
- Updates every 30 seconds in the background
- Makes status available without running git commands

## Project Structure

```
your-project/
├── .claude/
│   ├── critical_git_workflow.md    # Always visible
│   ├── important_code_style.md     # Frequently repeated
│   └── documentation_process.md    # Standard repetition
├── mcp_guidelines_server.py        # The MCP server
├── setup_claude_code.py           # Setup script
└── .mcp.json                      # Created by Claude Code (project scope)
```

## Configuration

### For Team Sharing

To share the MCP server configuration with your team:

1. Add the server with project scope:
   ```bash
   claude mcp add guidelines --scope project -- python mcp_guidelines_server.py .
   ```

2. This creates `.mcp.json` in your project root
3. Commit `.mcp.json` to version control
4. Team members will be prompted to approve the server when they open the project

### For Personal Use Across Projects

Add with user scope to use in all your projects:
```bash
claude mcp add guidelines --scope user -- python /absolute/path/to/mcp_guidelines_server.py
```

## Troubleshooting

### Server not appearing in Claude Code

1. Check if the server is registered:
   ```bash
   claude mcp list
   ```

2. If not listed, add it manually:
   ```bash
   claude mcp add guidelines -- python mcp_guidelines_server.py .
   ```

3. Restart Claude Code after adding

### Resources not showing with @

- Ensure the server is running (Claude Code starts it automatically)
- Try refreshing with `/mcp__guidelines__force_refresh`
- Check server logs in Claude Code output panel

### Guidelines not loading

- Ensure `.md` files are in `.claude/` directory
- Check file permissions
- Restart Claude Code after adding new files

## Advanced Usage

### Custom Repetition Intervals

When adding guidelines via the tool, specify custom intervals:

```
/mcp__guidelines__add_guideline
id: my_custom_rule
content: Always use type hints
priority: 9
repeat_after_tokens: 2000
```

### Environment Variables

Set MCP timeout if needed:
```bash
MCP_TIMEOUT=10000 claude code
```

Set maximum output tokens:
```bash
MAX_MCP_OUTPUT_TOKENS=50000 claude code
```

## Security Note

The server only has access to:
- The project directory you specify
- Git commands in that directory
- Reading/writing files in `.claude/` subdirectory

It does not have network access or ability to execute arbitrary commands.
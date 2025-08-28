#!/usr/bin/env python3
"""Prepare tool configuration for Claude Code execution.

This script generates settings JSON and claude_args for the new base action API.
"""

import argparse
import json
import os
from typing import List, Dict, Any


def get_base_tools(mode: str = None) -> str:
    """Get the base set of tools that are always included.
    
    Args:
        mode: The action mode (pr-gen, pr-update, plan-gen)

    """
    base_tools = [
        "Edit",
        "MultiEdit",
        "Read",
        "Write",
        "Glob",
        "Grep",
        "LS",
        "Bash(git:*)",
        "Bash(rg:*)",
        "Bash(gh pr:*)",  # Allow all GitHub CLI PR commands
        "Bash(gh auth:status)",  # Allow checking GitHub auth status
        "Bash(cat:*)",
        "Bash(rm:*)",
        "Bash(find:*)",  # Allow find commands for file searching
        "Bash(mv:*)",    # Allow move/rename commands
        "Task",
        "TodoWrite",
        "TodoRead",
    ]

    # Add MCP GitHub file operations tools for pr-update and pr-gen modes
    if mode in ["pr-update", "pr-gen"]:
        base_tools.extend([
            "mcp__github-file-ops__push_changes"
        ])

    return ",".join(base_tools)


def get_default_disallowed_tools() -> str:
    """Get the default set of tools that are disallowed."""
    disallowed_tools = [
        "WebFetch",
        "WebSearch",
    ]
    return ",".join(disallowed_tools)


def combine_tools(base_tools: str, additional_tools: str) -> str:
    """Combine base tools with additional allowed tools."""
    if additional_tools.strip():
        return f"{base_tools},{additional_tools}"
    return base_tools


def set_github_output(key: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    else:
        # For local testing, just print the output
        print(f"{key}={value}")


def generate_settings_json(mode: str, allowed_tools: str, disallowed_tools: str, 
                          model: str = None, max_turns: str = None, 
                          timeout_minutes: str = None, claude_env: str = None,
                          system_prompt: str = None) -> str:
    """Generate settings JSON for the new base action API."""
    settings = {}
    
    # Add model if specified
    if model:
        settings["model"] = model
    
    # Add system prompt if specified
    if system_prompt:
        settings["systemPrompt"] = system_prompt
    
    # Add max turns if specified
    if max_turns:
        try:
            settings["maxTurns"] = int(max_turns)
        except (ValueError, TypeError):
            pass
    
    # Add timeout if specified
    if timeout_minutes:
        try:
            settings["timeoutMinutes"] = int(timeout_minutes)
        except (ValueError, TypeError):
            pass
    
    # Add environment variables if specified
    if claude_env:
        settings["env"] = {}
        # Parse environment variables (expecting KEY=VALUE format)
        for env_var in claude_env.split(","):
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                settings["env"][key.strip()] = value.strip()
    
    # Add permissions for tools
    permissions = {}
    if allowed_tools:
        permissions["allow"] = [tool.strip() for tool in allowed_tools.split(",") if tool.strip()]
    if disallowed_tools:
        permissions["deny"] = [tool.strip() for tool in disallowed_tools.split(",") if tool.strip()]
    
    if permissions:
        settings["permissions"] = permissions
    
    return json.dumps(settings) if settings else ""


def generate_claude_args(mcp_config: str = None) -> str:
    """Generate claude_args for the new base action API."""
    args = []
    
    # Add MCP config if specified
    if mcp_config and mcp_config.strip():
        args.append(f"--mcp-config {mcp_config.strip()}")
    
    return "\n".join(args) if args else ""


def main() -> None:
    """Main function to prepare tool configuration."""
    parser = argparse.ArgumentParser(description="Prepare tool configuration for Claude Code")
    parser.add_argument(
        "--allowed-tools",
        default="",
        help="Additional tools to allow (comma-separated)"
    )
    parser.add_argument(
        "--disallowed-tools",
        default="",
        help="Tools to disallow (comma-separated)"
    )
    parser.add_argument(
        "--mode",
        default=None,
        help="Action mode (pr-gen, pr-update, plan-gen)"
    )

    args = parser.parse_args()

    # Get environment variables for the new inputs
    mode = args.mode or os.environ.get("DEVSY_MODE")
    model = os.environ.get("DEVSY_MODEL")
    max_turns = os.environ.get("DEVSY_MAX_TURNS")
    timeout_minutes = os.environ.get("DEVSY_TIMEOUT_MINUTES")
    claude_env = os.environ.get("DEVSY_CLAUDE_ENV")
    mcp_config = os.environ.get("DEVSY_MCP_CONFIG")
    system_prompt = os.environ.get("DEVSY_SYSTEM_PROMPT")

    # Get base tools and combine with additional tools
    base_tools = get_base_tools(mode)
    final_allowed_tools = combine_tools(base_tools, args.allowed_tools)

    # Get default disallowed tools and combine with user-provided ones
    default_disallowed = get_default_disallowed_tools()
    final_disallowed_tools = combine_tools(default_disallowed, args.disallowed_tools)

    # Generate settings JSON and claude_args
    settings_json = generate_settings_json(
        mode=mode,
        allowed_tools=final_allowed_tools,
        disallowed_tools=final_disallowed_tools,
        model=model,
        max_turns=max_turns,
        timeout_minutes=timeout_minutes,
        claude_env=claude_env,
        system_prompt=system_prompt
    )
    
    claude_args = generate_claude_args(mcp_config=mcp_config)

    # Set GitHub Actions outputs
    set_github_output("settings", settings_json)
    set_github_output("claude_args", claude_args)

    print("✅ Tool configuration prepared")
    print(f"📦 Base tools: {len(base_tools.split(','))} tools")
    if mode in ["pr-update", "pr-gen"]:
        print(f"🔧 MCP GitHub file operations tools enabled for {mode} mode")
    if args.allowed_tools:
        additional_count = len([t for t in args.allowed_tools.split(",") if t.strip()])
        print(f"➕ Additional tools: {additional_count} tools")

    # Show default + user disallowed tools
    default_disallowed_count = len(get_default_disallowed_tools().split(','))
    print(f"🚫 Default disallowed tools: {default_disallowed_count} tools (WebFetch, WebSearch)")

    if args.disallowed_tools:
        user_disallowed_count = len([t for t in args.disallowed_tools.split(",") if t.strip()])
        print(f"🚫 Additional disallowed tools: {user_disallowed_count} tools")
    
    if settings_json:
        print(f"⚙️ Generated settings JSON: {len(settings_json)} characters")
    if claude_args:
        print(f"🔧 Generated claude_args: {claude_args}")


if __name__ == "__main__":
    main()

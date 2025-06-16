#!/usr/bin/env python3
"""
Prepare tool configuration for Claude Code execution.

This script combines base tools with additional allowed tools and handles disallowed tools.
"""

import argparse
import os
from typing import List


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
    
    # Add MCP GitHub file operations tools for pr-update mode
    if mode == "pr-update":
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

    # Get base tools and combine with additional tools
    mode = args.mode or os.environ.get("DEVSY_MODE")
    base_tools = get_base_tools(mode)
    final_allowed_tools = combine_tools(base_tools, args.allowed_tools)

    # Get default disallowed tools and combine with user-provided ones
    default_disallowed = get_default_disallowed_tools()
    final_disallowed_tools = combine_tools(default_disallowed, args.disallowed_tools)

    # Set GitHub Actions outputs
    set_github_output("allowed_tools", final_allowed_tools)
    set_github_output("disallowed_tools", final_disallowed_tools)

    print("✅ Tool configuration prepared")
    print(f"📦 Base tools: {len(base_tools.split(','))} tools")
    if mode == "pr-update":
        print("🔧 MCP GitHub file operations tools enabled for pr-update mode")
    if args.allowed_tools:
        additional_count = len([t for t in args.allowed_tools.split(",") if t.strip()])
        print(f"➕ Additional tools: {additional_count} tools")
    
    # Show default + user disallowed tools
    default_disallowed_count = len(get_default_disallowed_tools().split(','))
    print(f"🚫 Default disallowed tools: {default_disallowed_count} tools (WebFetch, WebSearch)")
    
    if args.disallowed_tools:
        user_disallowed_count = len([t for t in args.disallowed_tools.split(",") if t.strip()])
        print(f"🚫 Additional disallowed tools: {user_disallowed_count} tools")


if __name__ == "__main__":
    main()
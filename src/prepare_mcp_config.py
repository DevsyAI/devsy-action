#!/usr/bin/env python3
"""
Prepare MCP configuration for Claude Code execution.

This script generates MCP server configuration for GitHub file operations
that can trigger checks when normal git operations might not.
"""

import json
import os
import sys


def generate_mcp_config(mode: str, github_token: str) -> str:
    """
    Generate MCP configuration based on the action mode.
    
    Args:
        mode: The action mode (pr-gen, pr-update, plan-gen)
        github_token: GitHub authentication token
        
    Returns:
        JSON string containing MCP configuration
    """
    # Only enable MCP server for pr-update mode
    if mode != "pr-update":
        return "{}"
    
    # Extract repository information from environment
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        print("⚠️  Could not determine repository owner/name from GITHUB_REPOSITORY")
        return "{}"
    
    owner, repo_name = repo.split("/", 1)
    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "main")
    
    # Generate MCP configuration
    config = {
        "mcpServers": {
            "github-file-ops": {
                "command": "python",
                "args": [
                    os.path.join(os.environ.get("GITHUB_ACTION_PATH", ""), "src/mcp/github_file_ops_server.py")
                ],
                "env": {
                    "GITHUB_TOKEN": github_token,
                    "REPO_OWNER": owner,
                    "REPO_NAME": repo_name,
                    "BRANCH_NAME": branch,
                    "PYTHONPATH": os.environ.get("GITHUB_ACTION_PATH", "")
                }
            }
        }
    }
    
    return json.dumps(config)


def set_github_output(key: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            # For JSON values, we need to escape properly
            if value.startswith("{"):
                # Write as a single line without newlines
                escaped_value = value.replace("\n", "")
                f.write(f"{key}={escaped_value}\n")
            else:
                f.write(f"{key}={value}\n")
    else:
        # For local testing
        print(f"{key}={value}")


def main() -> None:
    """Main function to prepare MCP configuration."""
    mode = os.environ.get("DEVSY_MODE", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    
    if not mode:
        print("❌ DEVSY_MODE environment variable not set")
        sys.exit(1)
    
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    # Generate MCP configuration
    mcp_config = generate_mcp_config(mode, github_token)
    
    # Set GitHub Actions output
    set_github_output("mcp_config", mcp_config)
    
    if mode == "pr-update" and mcp_config != "{}":
        print("✅ MCP configuration prepared for pr-update mode")
        print("🔧 GitHub file operations server enabled")
    else:
        print("ℹ️  MCP server not needed for this mode")


if __name__ == "__main__":
    main()
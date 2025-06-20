#!/usr/bin/env python3
"""
Prepare MCP configuration for Claude Code execution.

This script generates MCP server configuration for GitHub file operations
that can trigger checks when normal git operations might not.
"""

import json
import os
import sys


def generate_mcp_config(mode: str, github_token: str, pr_number: str = None) -> str:
    """
    Generate MCP configuration based on the action mode.
    
    Args:
        mode: The action mode (pr-gen, pr-update, plan-gen)
        github_token: GitHub authentication token
        pr_number: PR number for pr-update mode
        
    Returns:
        JSON string containing MCP configuration
    """
    # Only enable MCP server for pr-update and pr-gen modes
    if mode == "plan-gen":
        return '{"mcpServers": {}}'
    
    # Extract repository information from environment
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        print("⚠️  Could not determine repository owner/name from GITHUB_REPOSITORY")
        return '{"mcpServers": {}}'
    
    owner, repo_name = repo.split("/", 1)
    
    # For pr-update mode, fetch the PR's head branch
    if mode == "pr-update" and pr_number:
        try:
            import requests
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}"
            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {github_token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            response = requests.get(api_url, headers=headers)
            if response.ok:
                pr_data = response.json()
                branch = pr_data["head"]["ref"]
                print(f"🔧 Using PR head branch: {branch}")
            else:
                print(f"⚠️  Failed to fetch PR data: {response.status_code}")
                branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "main")
        except Exception as e:
            print(f"⚠️  Error fetching PR data: {e}")
            branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "main")
    else:
        branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "main")
    
    # Generate MCP configuration
    config = {
        "mcpServers": {
            "github-file-ops": {
                "command": "/tmp/devsy-action-env/bin/python",
                "args": [
                    os.path.join(os.environ.get("GITHUB_ACTION_PATH", ""), "src/mcp/github_file_ops_server.py")
                ],
                "env": {
                    "GITHUB_TOKEN": github_token,
                    "REPO_OWNER": owner,
                    "REPO_NAME": repo_name,
                    "BRANCH_NAME": branch,
                    "DEVSY_MODE": mode,
                    "DEVSY_BASE_BRANCH": os.environ.get("DEVSY_BASE_BRANCH", "main"),
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
    pr_number = os.environ.get("DEVSY_PR_NUMBER", "")
    
    if not mode:
        print("❌ DEVSY_MODE environment variable not set")
        sys.exit(1)
    
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    # Generate MCP configuration
    mcp_config = generate_mcp_config(mode, github_token, pr_number)
    
    # Set GitHub Actions output
    set_github_output("mcp_config", mcp_config)
    
    if mode in ["pr-update", "pr-gen"] and mcp_config != '{"mcpServers": {}}':
        print(f"✅ MCP configuration prepared for {mode} mode")
        print("🔧 GitHub file operations server enabled")
        print(f"🔧 [DEBUG] MCP config: {mcp_config}")
        
        # Test the server script exists and is executable
        script_path = os.path.join(os.environ.get("GITHUB_ACTION_PATH", ""), "src/mcp/github_file_ops_server.py")
        if os.path.exists(script_path):
            print(f"🔧 [DEBUG] ✅ Server script exists: {script_path}")
            if os.access(script_path, os.X_OK):
                print("🔧 [DEBUG] ✅ Server script is executable")
            else:
                print("🔧 [DEBUG] ❌ Server script is not executable")
        else:
            print(f"🔧 [DEBUG] ❌ Server script not found: {script_path}")
    else:
        print("ℹ️  MCP server not needed for this mode")


if __name__ == "__main__":
    main()
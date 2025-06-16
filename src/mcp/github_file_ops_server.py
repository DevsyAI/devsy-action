#!/usr/bin/env python3
"""
MCP Server for GitHub file operations.

This server provides tools for committing and deleting files in GitHub repositories
using the GitHub API directly. This approach can trigger GitHub checks when normal
git operations from actions might not.
"""

import asyncio
import os
import sys
import json
import base64
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    print("🔧 [DEBUG] ✅ MCP imports successful", file=sys.stderr)
except ImportError as e:
    print(f"🔧 [DEBUG] ❌ MCP import failed: {e}", file=sys.stderr)
    sys.exit(1)


def make_github_request(
    method: str,
    url: str,
    token: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make a request to the GitHub API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=data if data else None
    )
    
    if not response.ok:
        raise Exception(f"GitHub API error: {response.status_code} {response.text}")
    
    return response.json() if response.text else {}


def extract_local_commit_info(commit_ref: str = "HEAD") -> Dict[str, Any]:
    """Extract all details from a local commit."""
    
    try:
        # Get commit message
        message = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit_ref],
            capture_output=True, text=True, check=True, cwd=os.getcwd()
        ).stdout.strip()
        
        # Get author info
        author_name = subprocess.run(
            ["git", "log", "-1", "--pretty=%an", commit_ref],
            capture_output=True, text=True, check=True, cwd=os.getcwd()
        ).stdout.strip()
        
        author_email = subprocess.run(
            ["git", "log", "-1", "--pretty=%ae", commit_ref],
            capture_output=True, text=True, check=True, cwd=os.getcwd()
        ).stdout.strip()
        
        # Get list of files changed in this commit
        changed_files_output = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_ref],
            capture_output=True, text=True, check=True, cwd=os.getcwd()
        ).stdout.strip()
        
        changed_files = [f for f in changed_files_output.split('\n') if f.strip()]
        
        return {
            "message": message,
            "author_name": author_name,
            "author_email": author_email,
            "files": changed_files
        }
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to extract commit info: {e.stderr}")


def add_comment_impl(
    pr_number: int,
    body: str,
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a comment to a GitHub pull request.
    
    Args:
        pr_number: Pull request number
        body: Comment body (markdown supported)
        owner: Repository owner (optional, defaults to env var)
        repo: Repository name (optional, defaults to env var)
        github_token: GitHub authentication token (optional, defaults to env var)
    
    Returns:
        Dictionary with comment details including ID and URL
    """
    # Use environment variables as defaults
    owner = owner or os.environ.get('REPO_OWNER')
    repo = repo or os.environ.get('REPO_NAME')
    github_token = github_token or os.environ.get('GITHUB_TOKEN')
    
    if not all([owner, repo, github_token]):
        return {
            "success": False,
            "error": "Missing required parameters: owner, repo, or github_token"
        }
    
    if not body.strip():
        return {
            "success": False,
            "error": "Comment body cannot be empty"
        }
    
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    try:
        # Add comment to PR
        comment_data = make_github_request(
            "POST",
            f"{base_url}/issues/{pr_number}/comments",
            github_token,
            {"body": body}
        )
        
        return {
            "success": True,
            "comment_id": comment_data["id"],
            "url": comment_data["html_url"],
            "body": comment_data["body"],
            "message": f"Successfully added comment to PR #{pr_number}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def push_changes_impl(
    commit_ref: str = "HEAD",
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recreate a local commit on GitHub via API.
    
    This tool reads a local commit (including files modified by pre-commit hooks)
    and recreates it on GitHub using the GitHub API, ensuring checks are triggered.
    
    Args:
        commit_ref: Git reference to recreate (default: HEAD)
        owner: Repository owner (optional, defaults to env var)
        repo: Repository name (optional, defaults to env var)
        branch: Branch name (optional, defaults to env var)
        github_token: GitHub authentication token (optional, defaults to env var)
    
    Returns:
        Dictionary with commit details including SHA and URL
    """
    
    # Use environment variables as defaults
    owner = owner or os.environ.get('REPO_OWNER')
    repo = repo or os.environ.get('REPO_NAME')
    branch = branch or os.environ.get('BRANCH_NAME')
    github_token = github_token or os.environ.get('GITHUB_TOKEN')
    
    if not all([owner, repo, branch, github_token]):
        return {
            "success": False,
            "error": "Missing required parameters: owner, repo, branch, or github_token"
        }
    
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    try:
        # Extract local commit details
        commit_info = extract_local_commit_info(commit_ref)
        
        if not commit_info["files"]:
            return {
                "success": False,
                "error": "No files changed in the specified commit"
            }
        
        # Get current remote state
        ref_data = make_github_request(
            "GET",
            f"{base_url}/git/refs/heads/{branch}",
            github_token
        )
        base_sha = ref_data["object"]["sha"]
        
        # Get base tree
        base_commit = make_github_request(
            "GET",
            f"{base_url}/git/commits/{base_sha}",
            github_token
        )
        base_tree_sha = base_commit["tree"]["sha"]
        
        # Create blobs for all files in the working directory that were changed
        tree_entries = []
        for file_path in commit_info["files"]:
            if os.path.exists(file_path):
                # File exists - read current content (reflects pre-commit hook changes)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    encoding = "utf-8"
                except UnicodeDecodeError:
                    # Handle binary files
                    with open(file_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('utf-8')
                    encoding = "base64"
                
                # Create blob
                blob_data = make_github_request(
                    "POST",
                    f"{base_url}/git/blobs",
                    github_token,
                    {
                        "content": content,
                        "encoding": encoding
                    }
                )
                
                tree_entries.append({
                    "path": file_path,
                    "mode": "100644",  # Regular file
                    "type": "blob",
                    "sha": blob_data["sha"]
                })
            else:
                # File doesn't exist - this was a deletion
                tree_entries.append({
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": None  # Setting sha to null deletes the file
                })
        
        # Create tree
        tree_data = make_github_request(
            "POST",
            f"{base_url}/git/trees",
            github_token,
            {
                "base_tree": base_tree_sha,
                "tree": tree_entries
            }
        )
        new_tree_sha = tree_data["sha"]
        
        # Create commit with original message and author
        commit_data = make_github_request(
            "POST",
            f"{base_url}/git/commits",
            github_token,
            {
                "message": commit_info["message"],
                "tree": new_tree_sha,
                "parents": [base_sha],
                "author": {
                    "name": commit_info["author_name"],
                    "email": commit_info["author_email"]
                }
            }
        )
        new_commit_sha = commit_data["sha"]
        
        # Update branch reference
        ref_update = make_github_request(
            "PATCH",
            f"{base_url}/git/refs/heads/{branch}",
            github_token,
            {
                "sha": new_commit_sha,
                "force": False
            }
        )
        
        # Get original local commit SHA for reference
        try:
            original_sha = subprocess.run(
                ["git", "rev-parse", commit_ref],
                capture_output=True, text=True, check=True, cwd=os.getcwd()
            ).stdout.strip()
        except subprocess.CalledProcessError:
            original_sha = "unknown"
        
        return {
            "success": True,
            "original_local_sha": original_sha,
            "github_sha": new_commit_sha,
            "url": commit_data["html_url"],
            "message": f"Successfully recreated local commit with {len(commit_info['files'])} file(s)",
            "files_changed": commit_info["files"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }




# Create the MCP server
try:
    app = Server("GitHub File Operations", version="1.0.0")
    print("🔧 [DEBUG] ✅ MCP Server created successfully", file=sys.stderr)
except Exception as e:
    print(f"🔧 [DEBUG] ❌ Failed to create MCP Server: {e}", file=sys.stderr)
    sys.exit(1)


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="add_comment",
            description="Add a comment to a GitHub pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request number"
                    },
                    "body": {
                        "type": "string",
                        "description": "Comment body (markdown supported)"
                    },
                    "owner": {
                        "type": "string",
                        "description": "Repository owner (optional, defaults to env var)"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name (optional, defaults to env var)"
                    },
                    "github_token": {
                        "type": "string",
                        "description": "GitHub token (optional, defaults to env var)"
                    }
                },
                "required": ["pr_number", "body"]
            }
        ),
        types.Tool(
            name="push_changes",
            description="Recreate a local git commit on GitHub via API (includes pre-commit hook changes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit_ref": {
                        "type": "string",
                        "description": "Git reference to recreate (default: HEAD)"
                    },
                    "owner": {
                        "type": "string",
                        "description": "Repository owner (optional, defaults to env var)"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name (optional, defaults to env var)"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to env var)"
                    },
                    "github_token": {
                        "type": "string",
                        "description": "GitHub token (optional, defaults to env var)"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        if name == "add_comment":
            result = add_comment_impl(**arguments)
        elif name == "push_changes":
            result = push_changes_impl(**arguments)
        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }, indent=2)
        )]


async def main():
    """Run the MCP server."""
    print("🔧 [DEBUG] Starting MCP server main()", file=sys.stderr)
    
    # Check environment variables
    env_vars = ['GITHUB_TOKEN', 'REPO_OWNER', 'REPO_NAME', 'BRANCH_NAME']
    for var in env_vars:
        value = os.environ.get(var)
        status = "✅" if value else "❌"
        print(f"🔧 [DEBUG] {status} {var}: {'SET' if value else 'MISSING'}", file=sys.stderr)
    
    # Optional: set up uvloop for better performance
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("🔧 [DEBUG] ✅ uvloop enabled", file=sys.stderr)
    except ImportError:
        # uvloop is optional, fall back to default event loop
        print("🔧 [DEBUG] ℹ️ uvloop not available, using default event loop", file=sys.stderr)
    
    try:
        print("🔧 [DEBUG] Creating stdio_server...", file=sys.stderr)
        async with stdio_server() as (read_stream, write_stream):
            print("🔧 [DEBUG] stdio_server created, starting app.run...", file=sys.stderr)
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
            print("🔧 [DEBUG] app.run completed successfully", file=sys.stderr)
    except Exception as e:
        print(f"🔧 [DEBUG] ❌ Error in main(): {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise


if __name__ == "__main__":
    print("🔧 [DEBUG] Script starting...", file=sys.stderr)
    print(f"🔧 [DEBUG] Python version: {sys.version}", file=sys.stderr)
    print(f"🔧 [DEBUG] Python executable: {sys.executable}", file=sys.stderr)
    print(f"🔧 [DEBUG] Working directory: {os.getcwd()}", file=sys.stderr)
    print(f"🔧 [DEBUG] Script path: {__file__}", file=sys.stderr)
    
    # Test mode for debugging
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🔧 [DEBUG] TEST MODE: Server imports and creation successful!", file=sys.stderr)
        print("🔧 [DEBUG] TEST MODE: Environment variables:", file=sys.stderr)
        for var in ['GITHUB_TOKEN', 'REPO_OWNER', 'REPO_NAME', 'BRANCH_NAME']:
            value = os.environ.get(var)
            print(f"🔧 [DEBUG] TEST MODE: {var} = {'SET' if value else 'MISSING'}", file=sys.stderr)
        print("🔧 [DEBUG] TEST MODE: Exiting successfully", file=sys.stderr)
        sys.exit(0)
    
    try:
        print("🔧 [DEBUG] Calling asyncio.run(main())", file=sys.stderr)
        asyncio.run(main())
        print("🔧 [DEBUG] asyncio.run completed successfully", file=sys.stderr)
    except Exception as e:
        print(f"🔧 [DEBUG] ❌ Fatal error in __main__: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
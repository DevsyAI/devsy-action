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


def commit_files_impl(
    message: str,
    files: List[Dict[str, str]],
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Commit files to a GitHub repository.
    
    Args:
        message: Commit message
        files: List of file dictionaries with 'path' and 'content' keys
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
        # Get the current branch reference
        ref_data = make_github_request(
            "GET",
            f"{base_url}/git/refs/heads/{branch}",
            github_token
        )
        base_sha = ref_data["object"]["sha"]
        
        # Get the base commit
        base_commit = make_github_request(
            "GET",
            f"{base_url}/git/commits/{base_sha}",
            github_token
        )
        base_tree_sha = base_commit["tree"]["sha"]
        
        # Create tree entries for the files
        tree_entries = []
        for file in files:
            # Base64 encode the content
            content_b64 = base64.b64encode(file["content"].encode()).decode()
            tree_entries.append({
                "path": file["path"],
                "mode": "100644",  # Regular file
                "type": "blob",
                "content": file["content"]
            })
        
        # Create a new tree
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
        
        # Create the commit
        commit_data = make_github_request(
            "POST",
            f"{base_url}/git/commits",
            github_token,
            {
                "message": message,
                "tree": new_tree_sha,
                "parents": [base_sha]
            }
        )
        new_commit_sha = commit_data["sha"]
        
        # Update the branch reference
        ref_update = make_github_request(
            "PATCH",
            f"{base_url}/git/refs/heads/{branch}",
            github_token,
            {
                "sha": new_commit_sha,
                "force": False
            }
        )
        
        return {
            "success": True,
            "sha": new_commit_sha,
            "url": commit_data["html_url"],
            "message": f"Successfully committed {len(files)} file(s)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def delete_files_impl(
    message: str,
    paths: List[str],
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delete files from a GitHub repository.
    
    Args:
        message: Commit message
        paths: List of file paths to delete
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
        # Get the current branch reference
        ref_data = make_github_request(
            "GET",
            f"{base_url}/git/refs/heads/{branch}",
            github_token
        )
        base_sha = ref_data["object"]["sha"]
        
        # Get the base commit
        base_commit = make_github_request(
            "GET",
            f"{base_url}/git/commits/{base_sha}",
            github_token
        )
        base_tree_sha = base_commit["tree"]["sha"]
        
        # Get the current tree to find all files
        current_tree = make_github_request(
            "GET",
            f"{base_url}/git/trees/{base_tree_sha}?recursive=true",
            github_token
        )
        
        # Create new tree entries, excluding the files to delete
        tree_entries = []
        deleted_count = 0
        
        for item in current_tree["tree"]:
            if item["path"] not in paths:
                # Keep this file
                tree_entries.append({
                    "path": item["path"],
                    "mode": item["mode"],
                    "type": item["type"],
                    "sha": item["sha"]
                })
            else:
                deleted_count += 1
        
        # Create a new tree without the deleted files
        tree_data = make_github_request(
            "POST",
            f"{base_url}/git/trees",
            github_token,
            {
                "tree": tree_entries
            }
        )
        new_tree_sha = tree_data["sha"]
        
        # Create the commit
        commit_data = make_github_request(
            "POST",
            f"{base_url}/git/commits",
            github_token,
            {
                "message": message,
                "tree": new_tree_sha,
                "parents": [base_sha]
            }
        )
        new_commit_sha = commit_data["sha"]
        
        # Update the branch reference
        ref_update = make_github_request(
            "PATCH",
            f"{base_url}/git/refs/heads/{branch}",
            github_token,
            {
                "sha": new_commit_sha,
                "force": False
            }
        )
        
        return {
            "success": True,
            "sha": new_commit_sha,
            "url": commit_data["html_url"],
            "message": f"Successfully deleted {deleted_count} file(s)"
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
            name="commit_files",
            description="Commit files to a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "files": {
                        "type": "array",
                        "description": "List of files to commit",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "File path"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "File content"
                                }
                            },
                            "required": ["path", "content"]
                        }
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
                },
                "required": ["message", "files"]
            }
        ),
        types.Tool(
            name="delete_files",
            description="Delete files from a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "paths": {
                        "type": "array",
                        "description": "List of file paths to delete",
                        "items": {
                            "type": "string"
                        }
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
                },
                "required": ["message", "paths"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        if name == "commit_files":
            result = commit_files_impl(**arguments)
        elif name == "delete_files":
            result = delete_files_impl(**arguments)
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
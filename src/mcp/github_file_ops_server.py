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

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("GitHub File Operations")


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


@mcp.tool()
def commit_files(
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


@mcp.tool()
def delete_files(
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


if __name__ == "__main__":
    # Run the server
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        # uvloop is optional, fall back to default event loop
        pass
    
    # Run the MCP server
    asyncio.run(mcp.run())
#!/usr/bin/env python3
"""
Checkout the appropriate branch based on action mode.

For pr-update mode, checks out the PR's head branch to ensure changes
are made to the correct branch instead of the default branch.
"""

import os
import sys
import subprocess
import requests
from typing import Dict, Any


def fetch_github_data(endpoint: str, token: str) -> Dict[str, Any]:
    """Fetch data from GitHub API."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def run_git_command(command: list, description: str) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=os.getcwd()
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error {description}: {e.stderr}", file=sys.stderr)
        raise


def checkout_pr_branch(pr_number: int, github_token: str, repo: str) -> Dict[str, str]:
    """
    Checkout the head branch of a specific PR.
    
    Args:
        pr_number: The PR number to checkout
        github_token: GitHub authentication token
        repo: Repository in format "owner/repo"
    
    Returns:
        Dictionary with branch information and status
    """
    api_base = f"https://api.github.com/repos/{repo}"
    
    try:
        # Fetch PR data to get head branch information
        print(f"🔍 Fetching PR #{pr_number} data...", file=sys.stderr)
        pr_data = fetch_github_data(f"{api_base}/pulls/{pr_number}", token=github_token)
        
        head_branch = pr_data["head"]["ref"]
        head_repo = pr_data["head"]["repo"]["full_name"]
        base_branch = pr_data["base"]["ref"]
        
        print(f"📋 PR #{pr_number} Info:", file=sys.stderr)
        print(f"  - Head branch: {head_branch}", file=sys.stderr)
        print(f"  - Head repo: {head_repo}", file=sys.stderr)
        print(f"  - Base branch: {base_branch}", file=sys.stderr)
        
        # Check if this is a fork PR (head repo different from base repo)
        is_fork_pr = head_repo != repo
        
        if is_fork_pr:
            print(f"🍴 Fork PR detected: {head_repo} -> {repo}", file=sys.stderr)
            # For fork PRs, we need to add the fork as a remote and fetch from it
            fork_remote = "pr-fork"
            fork_url = f"https://github.com/{head_repo}.git"
            
            # Add fork remote (ignore if already exists)
            try:
                run_git_command(
                    ["git", "remote", "add", fork_remote, fork_url],  
                    "adding fork remote"
                )
                print(f"✅ Added fork remote: {fork_remote} -> {fork_url}", file=sys.stderr)
            except subprocess.CalledProcessError:
                # Remote probably already exists, continue
                print(f"ℹ️ Fork remote {fork_remote} already exists", file=sys.stderr)
            
            # Fetch from fork remote
            print(f"📥 Fetching from fork remote: {fork_remote}", file=sys.stderr)
            run_git_command(
                ["git", "fetch", fork_remote, head_branch],
                "fetching fork branch"
            )
            
            # Checkout the fork branch
            print(f"🔄 Checking out fork branch: {fork_remote}/{head_branch}", file=sys.stderr)
            run_git_command(
                ["git", "checkout", "-B", head_branch, f"{fork_remote}/{head_branch}"],
                "checking out fork branch"
            )
            
        else:
            # Same repo PR - standard checkout
            print(f"📥 Fetching branch from origin: {head_branch}", file=sys.stderr)
            run_git_command(
                ["git", "fetch", "origin", head_branch],
                "fetching branch"
            )
            
            print(f"🔄 Checking out branch: {head_branch}", file=sys.stderr)
            run_git_command(
                ["git", "checkout", head_branch],
                "checking out branch"
            )
        
        # Verify we're on the correct branch
        current_branch = run_git_command(["git", "branch", "--show-current"], "getting current branch")
        
        if current_branch != head_branch:
            raise Exception(f"Failed to checkout correct branch. Expected: {head_branch}, Got: {current_branch}")
            
        print(f"✅ Successfully checked out PR branch: {current_branch}", file=sys.stderr)
        
        return {
            "success": True,
            "head_branch": head_branch,
            "base_branch": base_branch,
            "current_branch": current_branch,
            "is_fork_pr": is_fork_pr,
            "head_repo": head_repo
        }
        
    except Exception as e:
        error_msg = f"Failed to checkout PR branch: {str(e)}"
        print(f"❌ {error_msg}", file=sys.stderr)
        return {
            "success": False,
            "error": error_msg
        }


def main():
    """Main function to handle branch checkout based on action mode."""
    # Read environment variables
    mode = os.environ.get("DEVSY_MODE", "")
    pr_number_str = os.environ.get("DEVSY_PR_NUMBER", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("DEVSY_REPO", "")
    
    # Validate required parameters
    if not mode:
        print("Error: DEVSY_MODE environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
        
    if not repo:
        print("Error: DEVSY_REPO environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    print(f"🚀 Branch checkout for mode: {mode}", file=sys.stderr)
    
    # Only checkout branch for pr-update mode
    if mode == "pr-update":
        if not pr_number_str:
            print("Error: DEVSY_PR_NUMBER environment variable is required for pr-update mode", file=sys.stderr)
            sys.exit(1)
            
        try:
            pr_number = int(pr_number_str)
        except ValueError:
            print(f"Error: Invalid PR number: {pr_number_str}", file=sys.stderr)
            sys.exit(1)
            
        result = checkout_pr_branch(pr_number, github_token, repo)
        
        if not result["success"]:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
            
        print(f"🎯 Ready to work on PR #{pr_number} (branch: {result['current_branch']})", file=sys.stderr)
        
    else:
        print(f"ℹ️ No branch checkout needed for mode: {mode}", file=sys.stderr)
    
    print("✅ Branch checkout completed successfully", file=sys.stderr)


if __name__ == "__main__":
    main()
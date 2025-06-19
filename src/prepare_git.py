#!/usr/bin/env python3
"""
Prepare Git environment for Devsy Action.

This script combines three previously separate steps:
1. Exchange GitHub Actions token for devsy-bot token
2. Configure Git identity based on token source
3. Checkout appropriate branch based on action mode

This consolidation improves readability, testability, and maintainability.
"""

import json
import os
import sys
import subprocess
from typing import Optional, Dict, Any

import requests


def set_github_output(name: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")

    # Always set as environment variable for the current process
    os.environ[name] = value


def get_oidc_token() -> str:
    """Get OIDC token from GitHub Actions environment."""
    # Get OIDC request environment variables
    token_request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL")
    token_request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    
    if not token_request_url or not token_request_token:
        raise ValueError(
            "OIDC token request environment variables not found. "
            "Did you remember to add 'id-token: write' to your workflow permissions?"
        )
    
    # Set audience for devsy-action
    audience = "devsy-action"
    
    # Request the OIDC token
    try:
        response = requests.get(
            f"{token_request_url}&audience={audience}",
            headers={
                "Authorization": f"Bearer {token_request_token}",
                "User-Agent": "actions/oidc-client"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("value")
        else:
            raise Exception(f"OIDC token request failed with status {response.status_code}: {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to request OIDC token: {e}")


def exchange_for_devsy_bot_token(oidc_token: str) -> Optional[str]:
    """Exchange OIDC token for devsy-bot installation token."""
    # Get backend URL (configurable for different environments)
    backend_url = os.getenv("DEVSY_BACKEND_URL", "https://devsy.ai")
    exchange_url = f"{backend_url}/api/github-app/oidc-token-exchange"

    # Make the token exchange request with OIDC token
    try:
        response = requests.post(
            exchange_url,
            headers={
                "Authorization": f"Bearer {oidc_token}",
                "Content-Type": "application/json", 
                "User-Agent": "devsy-action/1.0"
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("access_token")
        else:
            raise Exception(f"Token exchange failed with status {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to devsy backend: {e}")


def perform_token_exchange() -> tuple[str, str]:
    """
    Perform token exchange and return (github_token, token_source).
    
    Returns:
        Tuple of (github_token, token_source) where token_source is either
        'devsy-bot' or 'github-actions-bot'
    """
    print("🔄 Attempting to exchange GitHub Actions token for devsy-bot token...")

    # Check for override token first (for testing/debugging)
    override_token = os.getenv("OVERRIDE_GITHUB_TOKEN")
    if override_token:
        print("Using override GitHub token")
        return override_token, "github-actions-bot"

    # Try to get OIDC token and exchange for devsy-bot token
    try:
        oidc_token = get_oidc_token()
        devsy_token = exchange_for_devsy_bot_token(oidc_token)
        if devsy_token:
            print("Successfully exchanged token for devsy-bot")
            return devsy_token, "devsy-bot"
    except Exception as e:
        print(f"OIDC token exchange failed: {e}")
        print("Falling back to default GitHub token")

    # Fallback to default GitHub Actions token
    default_token = os.getenv("GITHUB_TOKEN")
    if not default_token:
        raise ValueError("GITHUB_TOKEN environment variable is required for fallback")
    
    print("Using default GitHub Actions token")
    return default_token, "github-actions-bot"


def run_command(command: list, description: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the completed process."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check,
            cwd=os.getcwd()
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error {description}: {e.stderr}", file=sys.stderr)
        raise


def configure_git_identity(github_token: str, token_source: str) -> None:
    """Configure Git identity based on token source."""
    print(f"🔧 Configuring Git identity for token source: {token_source}")
    
    if token_source == "devsy-bot":
        # Get the bot's identity dynamically for verified commits
        try:
            result = run_command(
                ["gh", "api", "user", "--jq", "{login: .login, id: .id}"],
                "getting bot identity"
            )
            bot_info = json.loads(result.stdout.strip())
            bot_login = bot_info["login"]
            bot_id = bot_info["id"]
            
            # Configure git with bot identity
            run_command(
                ["git", "config", "--global", "user.email", f"{bot_id}+{bot_login}@users.noreply.github.com"],
                "setting git email"
            )
            run_command(
                ["git", "config", "--global", "user.name", bot_login],
                "setting git name"
            )
            print(f"✅ Configured git identity for {bot_login} (ID: {bot_id})")
            
        except Exception as e:
            print(f"⚠️ Failed to get bot identity, using fallback: {e}")
            # Fallback to generic identity
            run_command(
                ["git", "config", "--global", "user.email", "no-reply@devsy.ai"],
                "setting fallback git email"
            )
            run_command(
                ["git", "config", "--global", "user.name", "devsy-bot"],
                "setting fallback git name"
            )
            print("✅ Configured git identity for Devsy Bot (fallback)")
    else:
        # Fallback to generic identity
        run_command(
            ["git", "config", "--global", "user.email", "no-reply@devsy.ai"],
            "setting git email"
        )
        run_command(
            ["git", "config", "--global", "user.name", "devsy-bot"],
            "setting git name"
        )
        print("✅ Configured git identity for Devsy Bot (fallback)")
    
    # Configure Git to use HTTPS instead of SSH for GitHub repositories
    # This enables pip to install private GitHub packages using the GitHub token
    run_command(
        ["git", "config", "--global", "url.https://github.com/.insteadOf", "git@github.com:"],
        "configuring git HTTPS"
    )


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


def checkout_pr_branch(pr_number: int, github_token: str, repo: str) -> Dict[str, Any]:
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
        print(f"🔍 Fetching PR #{pr_number} data...")
        pr_data = fetch_github_data(f"{api_base}/pulls/{pr_number}", token=github_token)
        
        head_branch = pr_data["head"]["ref"]
        head_repo = pr_data["head"]["repo"]["full_name"]
        base_branch = pr_data["base"]["ref"]
        
        print(f"📋 PR #{pr_number} Info:")
        print(f"  - Head branch: {head_branch}")
        print(f"  - Head repo: {head_repo}")
        print(f"  - Base branch: {base_branch}")
        
        # Check if this is a fork PR (head repo different from base repo)
        is_fork_pr = head_repo != repo
        
        if is_fork_pr:
            print(f"🍴 Fork PR detected: {head_repo} -> {repo}")
            # For fork PRs, we need to add the fork as a remote and fetch from it
            fork_remote = "pr-fork"
            fork_url = f"https://github.com/{head_repo}.git"
            
            # Add fork remote (ignore if already exists)
            try:
                run_git_command(
                    ["git", "remote", "add", fork_remote, fork_url],  
                    "adding fork remote"
                )
                print(f"✅ Added fork remote: {fork_remote} -> {fork_url}")
            except subprocess.CalledProcessError:
                # Remote probably already exists, continue
                print(f"ℹ️ Fork remote {fork_remote} already exists")
            
            # Fetch from fork remote
            print(f"📥 Fetching from fork remote: {fork_remote}")
            run_git_command(
                ["git", "fetch", fork_remote, head_branch],
                "fetching fork branch"
            )
            
            # Checkout the fork branch
            print(f"🔄 Checking out fork branch: {fork_remote}/{head_branch}")
            run_git_command(
                ["git", "checkout", "-B", head_branch, f"{fork_remote}/{head_branch}"],
                "checking out fork branch"
            )
            
        else:
            # Same repo PR - standard checkout
            print(f"📥 Fetching branch from origin: {head_branch}")
            run_git_command(
                ["git", "fetch", "origin", head_branch],
                "fetching branch"
            )
            
            print(f"🔄 Checking out branch: {head_branch}")
            run_git_command(
                ["git", "checkout", head_branch],
                "checking out branch"
            )
        
        # Verify we're on the correct branch
        current_branch = run_git_command(["git", "branch", "--show-current"], "getting current branch")
        
        if current_branch != head_branch:
            raise Exception(f"Failed to checkout correct branch. Expected: {head_branch}, Got: {current_branch}")
            
        print(f"✅ Successfully checked out PR branch: {current_branch}")
        
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


def handle_branch_checkout(mode: str, pr_number_str: str, github_token: str, repo: str) -> None:
    """Handle branch checkout based on action mode."""
    print(f"🚀 Branch checkout for mode: {mode}")
    
    # Only checkout branch for pr-update mode
    if mode == "pr-update":
        if not pr_number_str:
            raise ValueError("DEVSY_PR_NUMBER environment variable is required for pr-update mode")
            
        try:
            pr_number = int(pr_number_str)
        except ValueError:
            raise ValueError(f"Invalid PR number: {pr_number_str}")
            
        result = checkout_pr_branch(pr_number, github_token, repo)
        
        if not result["success"]:
            raise Exception(result["error"])
            
        print(f"🎯 Ready to work on PR #{pr_number} (branch: {result['current_branch']})")
        
    else:
        print(f"ℹ️ No branch checkout needed for mode: {mode}")
    
    print("✅ Branch checkout completed successfully")


def main():
    """Main function to prepare Git environment."""
    # Read environment variables
    mode = os.environ.get("DEVSY_MODE", "")
    pr_number_str = os.environ.get("DEVSY_PR_NUMBER", "")
    repo = os.environ.get("DEVSY_REPO", "")
    
    # Validate required parameters
    if not mode:
        print("Error: DEVSY_MODE environment variable is required", file=sys.stderr)
        sys.exit(1)
        
    if not repo:
        print("Error: DEVSY_REPO environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Step 1: Perform token exchange
        github_token, token_source = perform_token_exchange()
        
        # Set outputs for GitHub Actions
        set_github_output("github_token", github_token)
        set_github_output("token_source", token_source)
        
        # Set token for subsequent operations
        os.environ["GITHUB_TOKEN"] = github_token
        
        # Step 2: Configure Git identity
        configure_git_identity(github_token, token_source)
        
        # Step 3: Handle branch checkout
        handle_branch_checkout(mode, pr_number_str, github_token, repo)
        
        print("✅ Git environment preparation completed successfully")
        
    except Exception as e:
        print(f"❌ Error preparing Git environment: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
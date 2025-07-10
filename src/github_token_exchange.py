#!/usr/bin/env python3
"""GitHub token exchange script for Devsy Action.

This script exchanges a GitHub Actions OIDC token for a devsy-bot
GitHub App installation token, allowing PRs to be created as devsy-bot
instead of the generic github-actions bot.

Based on: https://github.com/anthropics/claude-code-action/blob/main/src/github/token.ts
"""

import json
import os
import sys
from typing import Optional

import requests


def get_github_token() -> str:
    """Get the GitHub token from environment or perform token exchange."""
    # Check for override token first (for testing/debugging)
    override_token = os.getenv("OVERRIDE_GITHUB_TOKEN")
    if override_token:
        print("Using override GitHub token")
        set_github_output("github_token", override_token)
        return override_token

    # Try to get OIDC token and exchange for devsy-bot token
    try:
        oidc_token = get_oidc_token()
        devsy_token = exchange_for_devsy_bot_token(oidc_token)
        if devsy_token:
            print("Successfully exchanged OIDC token for devsy-bot")
            set_github_output("github_token", devsy_token)
            return devsy_token
    except Exception as e:
        print(f"OIDC token exchange failed: {e}")
        print("Falling back to default GitHub token")

    # Fallback to default GitHub Actions token
    default_token = os.getenv("GITHUB_TOKEN")
    if not default_token:
        raise ValueError("GITHUB_TOKEN environment variable is required for fallback")

    print("Using default GitHub Actions token")
    set_github_output("github_token", default_token)
    return default_token


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


def set_github_output(name: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")

    # Always set as environment variable for the current process
    os.environ[name] = value


def main():
    """Main function to run token exchange."""
    try:
        token = get_github_token()
        print(f"GitHub token configured successfully")

        # Also set as environment variable for the current process
        os.environ["GITHUB_TOKEN"] = token

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

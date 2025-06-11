#!/usr/bin/env python3
"""
Send callback notification with execution results.

This script sends a POST request to the specified callback URL with the execution results.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests


def read_execution_file(execution_file: str) -> Optional[str]:
    """Read and return the execution file contents."""
    try:
        if execution_file and os.path.exists(execution_file):
            with open(execution_file, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"⚠️  Warning: Failed to read execution file {execution_file}: {e}")
    return None


def prepare_callback_data(
    run_id: str,
    run_url: str,
    mode: str,
    conclusion: str,
    pr_number: str,
    pr_url: str,
    plan_output: str,
    execution_file: str,
    token_source: str,
) -> Dict[str, Any]:
    """Prepare the callback data payload."""
    # Read execution file contents
    execution_file_contents = read_execution_file(execution_file)
    
    return {
        "run_id": run_id,
        "run_url": run_url,
        "mode": mode,
        "conclusion": conclusion,
        "pr_number": pr_number if pr_number else None,
        "pr_url": pr_url if pr_url else None,
        "plan_output": plan_output if plan_output else None,
        "execution_file": execution_file,
        "execution_file_contents": execution_file_contents,
        "token_source": token_source,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def prepare_headers(
    auth_token: str, auth_header: str, run_id: str, repository: str
) -> Dict[str, str]:
    """Prepare HTTP headers for the callback request."""
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Run-ID": run_id,
        "X-GitHub-Repository": repository,
    }

    # Add authentication if token provided
    if auth_token:
        header_name = auth_header if auth_header else "Authorization"
        headers[header_name] = f"Bearer {auth_token}"

    return headers


def send_callback(
    url: str,
    data: Dict[str, Any],
    headers: Dict[str, str],
    timeout: int = 30,
) -> bool:
    """Send the callback request."""
    try:
        response = requests.post(
            url, 
            json=data, 
            headers=headers, 
            timeout=timeout
        )
        response.raise_for_status()
        print(f"✅ Callback sent successfully to {url}")
        print(f"📊 Response status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Warning: Failed to send callback to {url}: {e}")
        print("(Action will continue anyway)")
        return False


def main() -> None:
    """Main function to send callback notification."""
    parser = argparse.ArgumentParser(description="Send callback notification")
    parser.add_argument("--callback-url", required=True, help="Callback URL")
    parser.add_argument("--run-id", required=True, help="GitHub run ID")
    parser.add_argument("--run-url", required=True, help="GitHub run URL")
    parser.add_argument("--mode", required=True, help="Action mode")
    parser.add_argument("--conclusion", required=True, help="Execution conclusion")
    parser.add_argument("--pr-number", default="", help="PR number")
    parser.add_argument("--pr-url", default="", help="PR URL")
    parser.add_argument("--plan-output", default="", help="Plan output")
    parser.add_argument("--execution-file", required=True, help="Execution file path")
    parser.add_argument("--token-source", required=True, help="Token source")
    parser.add_argument("--auth-token", default="", help="Authentication token")
    parser.add_argument("--auth-header", default="", help="Authentication header name")
    parser.add_argument("--repository", required=True, help="GitHub repository")

    args = parser.parse_args()

    # Prepare callback data
    callback_data = prepare_callback_data(
        args.run_id,
        args.run_url,
        args.mode,
        args.conclusion,
        args.pr_number,
        args.pr_url,
        args.plan_output,
        args.execution_file,
        args.token_source,
    )

    # Prepare headers
    headers = prepare_headers(
        args.auth_token, args.auth_header, args.run_id, args.repository
    )

    # Log callback attempt
    if args.auth_token:
        print(f"📤 Sending authenticated callback to {args.callback_url}")
    else:
        print(f"📤 Sending callback to {args.callback_url}")

    # Send callback
    success = send_callback(args.callback_url, callback_data, headers)
    
    # Exit with appropriate code (but don't fail the action on callback failure)
    sys.exit(0)


if __name__ == "__main__":
    main()
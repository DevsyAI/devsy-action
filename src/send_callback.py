#!/usr/bin/env python3
"""
Send callback notification with execution results.

This script sends a POST request to the specified callback URL with the execution results.
"""

import base64
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
    
    # Decode base64-encoded plan_output if present
    decoded_plan_output = None
    if plan_output:
        try:
            decoded_plan_output = base64.b64decode(plan_output).decode('utf-8')
        except Exception as e:
            print(f"⚠️  Warning: Failed to decode plan_output: {e}")
            decoded_plan_output = plan_output  # Fallback to raw value
    
    return {
        "run_id": run_id,
        "run_url": run_url,
        "mode": mode,
        "conclusion": conclusion,
        "pr_number": pr_number if pr_number else None,
        "pr_url": pr_url if pr_url else None,
        "plan_output": decoded_plan_output,
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
    # Read all parameters from environment variables
    callback_url = os.environ.get("DEVSY_CALLBACK_URL", "")
    run_id = os.environ.get("DEVSY_RUN_ID", "")
    run_url = os.environ.get("DEVSY_RUN_URL", "")
    mode = os.environ.get("DEVSY_MODE", "")
    conclusion = os.environ.get("DEVSY_CONCLUSION", "")
    pr_number = os.environ.get("DEVSY_PR_NUMBER", "")
    pr_url = os.environ.get("DEVSY_PR_URL", "")
    plan_output = os.environ.get("DEVSY_PLAN_OUTPUT", "")
    execution_file = os.environ.get("DEVSY_EXECUTION_FILE", "")
    token_source = os.environ.get("DEVSY_TOKEN_SOURCE", "")
    auth_token = os.environ.get("DEVSY_AUTH_TOKEN", "")
    auth_header = os.environ.get("DEVSY_AUTH_HEADER", "")
    repository = os.environ.get("DEVSY_REPOSITORY", "")
    
    # Validate required parameters
    if not callback_url:
        print("Error: DEVSY_CALLBACK_URL environment variable is required")
        sys.exit(1)
    if not run_id:
        print("Error: DEVSY_RUN_ID environment variable is required")
        sys.exit(1)
    if not run_url:
        print("Error: DEVSY_RUN_URL environment variable is required")
        sys.exit(1)
    if not mode:
        print("Error: DEVSY_MODE environment variable is required")
        sys.exit(1)
    if not conclusion:
        print("Error: DEVSY_CONCLUSION environment variable is required")
        sys.exit(1)
    if not execution_file:
        print("Error: DEVSY_EXECUTION_FILE environment variable is required")
        sys.exit(1)
    if not token_source:
        print("Error: DEVSY_TOKEN_SOURCE environment variable is required")
        sys.exit(1)
    if not repository:
        print("Error: DEVSY_REPOSITORY environment variable is required")
        sys.exit(1)

    # Prepare callback data
    callback_data = prepare_callback_data(
        run_id,
        run_url,
        mode,
        conclusion,
        pr_number,
        pr_url,
        plan_output,
        execution_file,
        token_source,
    )

    # Prepare headers
    headers = prepare_headers(
        auth_token, auth_header, run_id, repository
    )

    # Log callback attempt
    if auth_token:
        print(f"📤 Sending authenticated callback to {callback_url}")
    else:
        print(f"📤 Sending callback to {callback_url}")

    # Send callback
    success = send_callback(callback_url, callback_data, headers)
    
    # Exit with appropriate code (but don't fail the action on callback failure)
    sys.exit(0)


if __name__ == "__main__":
    main()
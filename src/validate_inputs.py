#!/usr/bin/env python3
"""Validate inputs for the Devsy Action.

This script validates the required inputs for different modes and authentication methods.
"""

import os
import sys
from typing import List


def validate_mode(mode: str) -> None:
    """Validate the action mode."""
    valid_modes = ["pr-gen", "pr-update", "pr-review", "plan-gen"]
    if mode not in valid_modes:
        print(f"Error: Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}")
        sys.exit(1)


def validate_authentication(
    anthropic_api_key: str, use_bedrock: str, use_vertex: str
) -> None:
    """Validate authentication configuration."""
    if not anthropic_api_key and use_bedrock != "true" and use_vertex != "true":
        error_lines = [
            "Error: Authentication required. Please provide one of:",
            "  - anthropic_api_key: Set up ANTHROPIC_API_KEY in repository secrets",
            "  - use_bedrock: true (with appropriate AWS credentials)",
            "  - use_vertex: true (with appropriate GCP credentials)",
            "",
            "To set up ANTHROPIC_API_KEY:",
            "  1. Go to your repository Settings > Secrets and variables > Actions",
            "  2. Click 'New repository secret'",
            "  3. Name: ANTHROPIC_API_KEY",
            "  4. Value: Your Anthropic API key from console.anthropic.com",
        ]
        for line in error_lines:
            print(line)
        sys.exit(1)


def validate_mode_requirements(
    mode: str, prompt: str, prompt_file: str, pr_number: str
) -> None:
    """Validate mode-specific requirements."""
    if mode == "pr-gen" and not prompt and not prompt_file:
        print("Error: prompt or prompt_file is required for pr-gen mode")
        sys.exit(1)

    if mode == "pr-update" and not pr_number:
        print("Error: pr_number is required for pr-update mode")
        sys.exit(1)

    if mode == "pr-review" and not pr_number:
        print("Error: pr_number is required for pr-review mode")
        sys.exit(1)


def main() -> None:
    """Main validation function."""
    # Read all parameters from environment variables
    mode = os.environ.get("DEVSY_MODE", "")
    anthropic_api_key = os.environ.get("DEVSY_ANTHROPIC_API_KEY", "")
    use_bedrock = os.environ.get("DEVSY_USE_BEDROCK", "false")
    use_vertex = os.environ.get("DEVSY_USE_VERTEX", "false")
    prompt = os.environ.get("DEVSY_PROMPT", "")
    prompt_file = os.environ.get("DEVSY_PROMPT_FILE", "")
    pr_number = os.environ.get("DEVSY_PR_NUMBER", "")

    # Validate mode is provided
    if not mode:
        print("Error: DEVSY_MODE environment variable is required")
        sys.exit(1)

    # Run all validations
    validate_mode(mode)
    validate_authentication(anthropic_api_key, use_bedrock, use_vertex)
    validate_mode_requirements(mode, prompt, prompt_file, pr_number)

    print("✅ All input validations passed")


if __name__ == "__main__":
    main()

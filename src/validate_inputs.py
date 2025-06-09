#!/usr/bin/env python3
"""
Validate inputs for the Devsy Action.

This script validates the required inputs for different modes and authentication methods.
"""

import argparse
import sys
from typing import List


def validate_mode(mode: str) -> None:
    """Validate the action mode."""
    valid_modes = ["pr-gen", "pr-update", "plan-gen"]
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


def main() -> None:
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate Devsy Action inputs")
    parser.add_argument("--mode", required=True, help="Action mode")
    parser.add_argument("--anthropic-api-key", default="", help="Anthropic API key")
    parser.add_argument("--use-bedrock", default="false", help="Use AWS Bedrock")
    parser.add_argument("--use-vertex", default="false", help="Use Google Vertex")
    parser.add_argument("--prompt", default="", help="User prompt")
    parser.add_argument("--prompt-file", default="", help="Prompt file path")
    parser.add_argument("--pr-number", default="", help="PR number for updates")

    args = parser.parse_args()

    # Run all validations
    validate_mode(args.mode)
    validate_authentication(args.anthropic_api_key, args.use_bedrock, args.use_vertex)
    validate_mode_requirements(args.mode, args.prompt, args.prompt_file, args.pr_number)

    print("✅ All input validations passed")


if __name__ == "__main__":
    main()
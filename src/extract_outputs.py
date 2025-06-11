#!/usr/bin/env python3
"""Extract outputs from Claude's execution results for GitHub Actions."""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def extract_github_urls(text):
    """Extract GitHub URLs (PRs, issues, etc.) from text."""
    # Match GitHub URLs for PRs, issues, commits, etc.
    github_url_pattern = r"https://github\.com/[^/\s]+/[^/\s]+/(?:pull|issues|commit)/\d+"
    urls = re.findall(github_url_pattern, text)
    return urls


def extract_pr_numbers(text):
    """Extract PR numbers from text."""
    # Look for PR references like #123, PR #123, pull request #123, etc.
    pr_patterns = [
        r"(?:PR|Pull Request|pull request)\s*#(\d+)",
        r"#(\d+)",  # Generic number reference
        r"pull/(\d+)",  # From URLs
    ]

    numbers = []
    for pattern in pr_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        numbers.extend(matches)

    return [int(num) for num in numbers if num.isdigit()]


def extract_branch_names(text):
    """Extract branch names from text."""
    # Look for branch references
    branch_patterns = [
        r'(?:branch|Branch)\s+["\']?([a-zA-Z0-9/_-]+)["\']?',
        r'(?:created|Created)\s+(?:branch\s+)?["\']?([a-zA-Z0-9/_-]+)["\']?',
        r"(?:feat|fix|refactor|chore)/([a-zA-Z0-9/_-]+)",
    ]

    branches = []
    for pattern in branch_patterns:
        matches = re.findall(pattern, text)
        branches.extend(matches)

    return list(set(branches))  # Remove duplicates


def parse_execution_file(file_path):
    """Parse Claude's execution file to extract relevant information."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Execution file not found: {file_path}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Error reading execution file: {e}", file=sys.stderr)
        return {}

    # Extract various outputs
    github_urls = extract_github_urls(content)
    pr_numbers = extract_pr_numbers(content)
    branch_names = extract_branch_names(content)

    # Find PR URLs specifically
    pr_urls = [url for url in github_urls if "/pull/" in url]

    # Get the most recent/relevant PR number and URL
    latest_pr_number = pr_numbers[-1] if pr_numbers else None
    latest_pr_url = pr_urls[-1] if pr_urls else None

    return {
        "pr_number": str(latest_pr_number) if latest_pr_number else "",
        "pr_url": latest_pr_url or "",
        "branch_names": branch_names,
        "github_urls": github_urls,
        "content_length": len(content),
    }


def extract_plan_content(content):
    """Extract plan content for plan-gen mode."""
    if not content:
        return ""
    
    # Look for markdown code block containing the plan
    import re
    
    # Pattern to match ```markdown ... ``` blocks
    pattern = r'```markdown\s*(.*?)\s*```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    if matches:
        # Return the content from the first markdown block found
        return matches[0].strip()
    
    # Fallback: return the whole content if no markdown block found
    return content.strip()


def main():
    parser = argparse.ArgumentParser(description="Extract outputs from Claude execution")
    parser.add_argument("--execution-file", required=True, help="Path to Claude's execution file")
    parser.add_argument("--mode", required=True, choices=["pr-gen", "pr-update", "plan-gen"])

    args = parser.parse_args()

    # Parse the execution file
    outputs = parse_execution_file(args.execution_file)

    # Mode-specific processing
    if args.mode == "plan-gen":
        try:
            with open(args.execution_file, "r", encoding="utf-8") as f:
                plan_content = f.read()
            outputs["plan_output"] = extract_plan_content(plan_content)
        except Exception as e:
            print(f"Error reading plan content: {e}", file=sys.stderr)
            outputs["plan_output"] = ""
    else:
        outputs["plan_output"] = ""

    # Output for GitHub Actions
    github_output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")

    try:
        with open(github_output_file, "a") as f:
            f.write(f"pr_number={outputs.get('pr_number', '')}\n")
            f.write(f"pr_url={outputs.get('pr_url', '')}\n")
            
            # Use multiline delimiter for plan_output to avoid shell parsing issues
            plan_output = outputs.get('plan_output', '')
            delimiter = "EOF_PLAN_OUTPUT"
            f.write(f"plan_output<<{delimiter}\n")
            f.write(f"{plan_output}\n")
            f.write(f"{delimiter}\n")

            # Debug info (not used as outputs but helpful for troubleshooting)
            f.write(f"branch_names={json.dumps(outputs.get('branch_names', []))}\n")
            f.write(f"github_urls={json.dumps(outputs.get('github_urls', []))}\n")

    except Exception as e:
        print(f"Error writing outputs: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

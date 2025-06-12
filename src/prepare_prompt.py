#!/usr/bin/env python3
"""Prepare the prompt for Claude Code based on the action mode."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


def load_template(template_name):
    """Load a template file from the templates directory."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.parent
    template_path = script_dir / "templates" / f"{template_name}.md"

    with open(template_path, "r") as f:
        return f.read()


def render_template(template, **kwargs):
    """Simple template rendering with {{ variable }} replacement."""
    result = template
    for key, value in kwargs.items():
        # Replace {{ key }} with value, handling None values
        placeholder = f"{{{{ {key} }}}}"
        replacement = str(value) if value is not None else ""
        result = result.replace(placeholder, replacement)
    return result


def fetch_github_data(endpoint, token):
    """Fetch data from GitHub API."""
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def prepare_pr_gen_prompt(user_prompt, custom_instructions, repo_name, base_branch):
    """Prepare prompt for PR generation mode."""
    template = load_template("pr-gen")
    return render_template(
        template,
        user_prompt=user_prompt,
        custom_instructions=custom_instructions,
        repo_name=repo_name,
        base_branch=base_branch,
    )


def get_recent_feedback(pr_number, repo, token):
    """Get feedback since the last commit, including both conversation and file-level comments."""
    api_base = f"https://api.github.com/repos/{repo}"

    # Get last commit date
    commits = fetch_github_data(f"{api_base}/pulls/{pr_number}/commits", token)
    last_commit_date = commits[-1]["commit"]["committer"]["date"] if commits else None

    # Get both types of comments
    issue_comments = fetch_github_data(f"{api_base}/issues/{pr_number}/comments", token)
    review_comments = fetch_github_data(
        f"{api_base}/pulls/{pr_number}/comments", token
    )  # File-level comments

    if last_commit_date:
        recent_comments = [c for c in issue_comments + review_comments if c["created_at"] > last_commit_date]
        context = f"Comments since last commit ({last_commit_date}):"
    else:
        recent_comments = issue_comments + review_comments
        context = "All comments (no previous commits):"

    return context, recent_comments


def prepare_pr_update_prompt(pr_number, repo, token, custom_instructions, user_prompt, base_branch):
    """Prepare prompt for PR update mode."""
    api_base = f"https://api.github.com/repos/{repo}"
    pr_data = fetch_github_data(f"{api_base}/pulls/{pr_number}", token)

    # Get recent feedback since last commit
    context, recent_comments = get_recent_feedback(pr_number, repo, token)

    # Format comments with context about their type
    comments_text_parts = []
    for comment in recent_comments:
        comment_type = "file comment" if "path" in comment else "conversation comment"
        location = f" on {comment['path']}" if "path" in comment else ""
        comments_text_parts.append(
            f"@{comment['user']['login']} ({comment_type}{location}):\n{comment['body']}"
        )

    comments_text = "\n\n".join(comments_text_parts) if comments_text_parts else "No recent comments."

    template = load_template("pr-update")
    return render_template(
        template,
        repo_name=repo,
        base_branch=base_branch,
        pr_number=pr_number,
        pr_title=pr_data["title"],
        pr_body=pr_data["body"] or "No description provided.",
        feedback_context=context,
        comments_text=comments_text,
        additional_instructions=f"Additional instructions: {user_prompt}" if user_prompt else "",
        custom_instructions=custom_instructions,
    )


def prepare_plan_gen_prompt(user_prompt, custom_instructions, repo_name, base_branch):
    """Prepare prompt for plan generation mode."""
    template = load_template("plan-gen")
    return render_template(
        template,
        user_prompt=user_prompt,
        custom_instructions=custom_instructions,
        repo_name=repo_name,
        base_branch=base_branch,
    )


def main():
    parser = argparse.ArgumentParser(description="Prepare prompt for Claude Code")
    parser.add_argument("--mode", required=True, choices=["pr-gen", "pr-update", "plan-gen"])
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--custom-instructions", default="")
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base-branch", default="main")

    args = parser.parse_args()

    # Read prompt from file if provided
    user_prompt = args.prompt or ""
    if args.prompt_file and os.path.exists(args.prompt_file):
        with open(args.prompt_file, "r") as f:
            user_prompt = f.read().strip()

    try:
        # Load mode-specific system prompt
        system_prompt = load_template(f"system-prompt-{args.mode}")

        # Prepare user prompt based on mode
        if args.mode == "pr-gen":
            user_prompt_formatted = prepare_pr_gen_prompt(
                user_prompt, args.custom_instructions, args.repo, args.base_branch
            )
        elif args.mode == "pr-update":
            user_prompt_formatted = prepare_pr_update_prompt(
                args.pr_number,
                args.repo,
                args.github_token,
                args.custom_instructions,
                user_prompt,
                args.base_branch,
            )
        elif args.mode == "plan-gen":
            user_prompt_formatted = prepare_plan_gen_prompt(
                user_prompt, args.custom_instructions, args.repo, args.base_branch
            )

        # Output for GitHub Actions using JSON serialization for shell safety
        with open(os.environ.get("GITHUB_OUTPUT", "/dev/stdout"), "a") as f:
            # Use jq-compatible JSON serialization to handle untrusted content safely
            import subprocess
            
            # Serialize system_prompt using jq for shell safety
            # Use -Rs to read entire input as single string, then remove trailing newline in jq
            system_prompt_json = subprocess.run(
                ["jq", "-Rs", "rtrimstr(\"\\n\")"],
                input=system_prompt,
                text=True,
                capture_output=True,
                check=True
            ).stdout.strip()
            
            # Serialize user_prompt using jq for shell safety  
            user_prompt_json = subprocess.run(
                ["jq", "-Rs", "rtrimstr(\"\\n\")"],
                input=user_prompt_formatted,
                text=True,
                capture_output=True,
                check=True
            ).stdout.strip()
            
            f.write(f"system_prompt={system_prompt_json}\n")
            f.write(f"user_prompt={user_prompt_json}\n")

    except Exception as e:
        print(f"Error preparing prompt: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

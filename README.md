# Devsy Action

A GitHub Action that leverages Claude Code to automatically generate pull requests, update existing PRs based on feedback, or create implementation plans. Designed to be triggered via `workflow_dispatch` for remote execution with optional callback support.

## Features

- **PR Generation (`pr-gen`)**: Create pull requests from arbitrary prompts
- **PR Updates (`pr-update`)**: Update existing PRs based on review feedback
- **Plan Generation (`plan-gen`)**: Generate detailed implementation plans without making code changes
- **Remote Triggering**: Designed for `workflow_dispatch` to be called programmatically
- **Callback Support**: Optional webhook callback when execution completes

## Setup

### Required: Anthropic API Key

Before using this action, you need to set up authentication. The easiest method is to add your Anthropic API key to repository secrets:

1. **Get an API key**: Visit [console.anthropic.com](https://console.anthropic.com) to get your API key
2. **Add to repository secrets**:
   - Go to your repository **Settings** > **Secrets and variables** > **Actions**
   - Click **"New repository secret"**
   - **Name**: `ANTHROPIC_API_KEY`
   - **Value**: Your Anthropic API key

### Alternative Authentication

Instead of an API key, you can use:
- **AWS Bedrock**: Set `use_bedrock: true` (requires AWS credentials)
- **Google Vertex**: Set `use_vertex: true` (requires GCP credentials)

## Usage

This action is designed to be triggered remotely via GitHub's workflow_dispatch API:

### Remote Triggering via API

```bash
# Trigger PR generation for Node.js project
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/{owner}/{repo}/actions/workflows/devsy-action.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "mode": "pr-gen",
      "prompt": "Add a new endpoint /api/health that returns {status: ok}",
      "custom_instructions": "Follow our coding standards",
      "callback_url": "https://your-app.com/webhook/github-action-complete"
    }
  }'

# Trigger PR update
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/{owner}/{repo}/actions/workflows/devsy-action.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "mode": "pr-update",
      "pr_number": "456",
      "prompt": "Address the review feedback about error handling",
      "callback_url": "https://your-app.com/webhook/github-action-complete"
    }
  }'

# Trigger plan generation
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/{owner}/{repo}/actions/workflows/devsy-action.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "mode": "plan-gen",
      "prompt": "Create a plan for implementing OAuth2 authentication",
      "callback_url": "https://your-app.com/webhook/github-action-complete"
    }
  }'
```

### Workflow Definition

Place this in `.github/workflows/devsy-action.yml`:

```yaml
name: Devsy Action

on:
  workflow_dispatch:
    inputs:
      mode:
        description: 'Action mode: pr-gen, pr-update, or plan-gen'
        required: true
        type: choice
        options:
          - pr-gen
          - pr-update
          - plan-gen
      pr_number:
        description: 'PR number (required for pr-update mode)'
        required: false
        type: string
      prompt:
        description: 'Prompt for Claude'
        required: false
        type: string
      custom_instructions:
        description: 'Additional custom instructions'
        required: false
        type: string
      callback_url:
        description: 'URL to send completion callback'
        required: false
        type: string

jobs:
  run-devsy-action:
    runs-on: ubuntu-latest
    steps:
      - uses: DevsyAI/devsy-action@main
        id: devsy
        with:
          mode: ${{ inputs.mode }}
          pr_number: ${{ inputs.pr_number }}
          prompt: ${{ inputs.prompt }}
          custom_instructions: ${{ inputs.custom_instructions }}
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Inputs

### Required Inputs

- `mode`: Action mode - must be one of: `pr-gen`, `pr-update`, or `plan-gen`
- `anthropic_api_key`: Your Anthropic API key (or use `use_bedrock`/`use_vertex` for cloud providers)

### Mode-Specific Inputs

**For `pr-gen` mode:**
- `prompt`: The implementation prompt (what changes to make)

**For `pr-update` mode:**
- `pr_number`: The pull request number to update
- `prompt`: Additional instructions for the update (optional)

**For `plan-gen` mode:**
- `prompt`: The planning prompt

### Optional Inputs

- `model`: Claude model to use (default: `sonnet`)
- `prompt_file`: Path to a file containing the prompt (alternative to `prompt`)
- `custom_instructions`: Additional instructions for Claude
- `allowed_tools`: Additional tools for Claude to use (base tools are always included)
- `disallowed_tools`: Additional tools to disallow beyond the defaults (WebFetch, WebSearch)
- `base_branch`: Base branch for new PRs (default: `main`)
- `callback_url`: URL to POST completion status and results
- `callback_auth_token`: Bearer token for callback authentication
- `callback_auth_header`: Custom auth header name (default: `Authorization`)
- `max_turns`: Maximum number of conversation turns for Claude (default: `200`)
- `timeout_minutes`: Timeout in minutes for Claude Code execution (default: `10`)

### Tool Configuration

The action includes a comprehensive set of base tools that are always available:

**Base Tools (Always Included):**
- **File Operations**: `Edit`, `Read`, `Write`, `Glob`, `Grep`, `LS`
- **Git Commands**: `Bash(git:*)` - All git operations
- **Search**: `Bash(rg:*)` - Ripgrep for fast code search
- **Task Management**: `Task`, `TodoWrite`, `TodoRead`
- **GitHub CLI**: `Bash(gh pr:*)` - GitHub CLI PR commands

**Default Disallowed Tools:**
- `WebFetch` - Web content fetching
- `WebSearch` - Web search functionality

**Additional Tools**: Use `allowed_tools` to add more tools like:
- `Bash(npm install)` - Specific npm commands
- `Bash(pytest)` - Python testing
- `WebSearch` - Internet search capabilities

**Restricting Tools**: Use `disallowed_tools` to prevent specific tools:
- `Bash(rm:*)` - Prevent file deletion
- `Task` - Disable task management

Example:
```yaml
allowed_tools: "Bash(npm install),Bash(npm test),WebSearch"
disallowed_tools: "Bash(rm:*),Bash(sudo:*)"
```

### GitHub Authentication

The action uses an intelligent authentication system that provides the best user experience:

**Primary: devsy-bot GitHub App** (Recommended)
- Automatically attempts to exchange GitHub Actions token for devsy-bot access token
- Works without requiring repository "Allow GitHub Actions to create PRs" setting
- Provides devsy-bot branding on PRs and commits
- No additional setup required if devsy-bot is installed

**Fallback: GitHub Actions bot**
- Falls back gracefully if devsy-bot is not installed or unavailable
- Uses standard GitHub Actions bot token
- Requires "Allow GitHub Actions to create and approve pull requests" in repository settings
- Still provides full functionality

**Authentication Status**
- Check the `token_source` output to see which method was used
- View logs for detailed authentication flow information

### Cloud Provider Authentication

**AWS Bedrock**
- Set `use_bedrock: true`
- Configure region and credentials via environment variables:
  - `AWS_REGION`: AWS region (e.g., `us-east-1`)
  - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: AWS credentials
  - Or use IAM roles for GitHub Actions

**Google Vertex AI**
- Set `use_vertex: true`
- Configure project and region via environment variables:
  - `ANTHROPIC_VERTEX_PROJECT_ID`: Your GCP project ID
  - `CLOUD_ML_REGION`: GCP region (e.g., `us-central1`)
  - `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file

Example with AWS Bedrock:
```yaml
- uses: DevsyAI/devsy-action@main
  with:
    mode: pr-gen
    prompt: "Add authentication"
    use_bedrock: true
  env:
    AWS_REGION: us-west-2
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Outputs

- `conclusion`: Execution status (`success`, `failure`, or `no_changes`)
- `execution_file`: Path to the Claude Code execution log
- `pr_number`: PR number (for `pr-gen` and `pr-update` modes)
- `pr_url`: PR URL (for `pr-gen` and `pr-update` modes)
- `plan_output`: Generated plan content (for `plan-gen` mode)
- `token_source`: Authentication method used (`devsy-bot` or `github-actions-bot`)

## Callback Format

When a `callback_url` is provided, the action will send a POST request with the following JSON payload:

```json
{
  "run_id": "1234567890",
  "run_url": "https://github.com/owner/repo/actions/runs/1234567890",
  "mode": "pr-gen",
  "conclusion": "success",
  "pr_number": "123",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "plan_output": null,
  "execution_file": "claude-execution.json",
  "token_source": "devsy-bot",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Examples

### Python Script to Trigger Action

```python
import requests
import time

def trigger_devsy_action(
    repo_owner: str,
    repo_name: str,
    github_token: str,
    mode: str,
    **inputs
):
    """Trigger Devsy Action via GitHub API."""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/devsy-action.yml/dispatches"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "ref": "main",
        "inputs": {
            "mode": mode,
            **inputs
        }
    }

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()

    # Get run ID from the response
    # Note: You may need to poll the runs API to get the actual run ID
    return response

# Example usage
response = trigger_devsy_action(
    repo_owner="myorg",
    repo_name="myrepo",
    github_token="ghp_...",
    mode="pr-gen",
    prompt="Add user authentication with JWT tokens",
    custom_instructions="Follow TypeScript best practices",
    callback_url="https://myapp.com/github-webhook"
)
```

### Integration with SQS Queue Replacement

```python
# Instead of sending to SQS:
# sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(task_data))

# Trigger GitHub Action:
response = trigger_devsy_action(
    repo_owner=repo_owner,
    repo_name=repo_name,
    github_token=github_token,
    mode="pr-gen",
    prompt=task_description,
    callback_url=f"{base_url}/api/github-action-callback/{task_id}"
)
```

## Setup and Dependencies

### Custom Setup Script

The action looks for a `.devsy/setup.sh` script in your repository root and runs it before executing Claude Code. This allows you to:

- Install dependencies specific to your project
- Set up development environment
- Run build steps or other preparation tasks

Create `.devsy/setup.sh` in your repository:

```bash
#!/bin/bash
set -e

echo "Setting up project dependencies..."

# Install Node.js dependencies
if [ -f "package.json" ]; then
    npm install
fi

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
    pip install .
fi

# Custom build steps
npm run build

echo "Setup complete!"
```

**Important**: Make sure your setup script is executable (`chmod +x .devsy/setup.sh`) and includes proper error handling.

## Customization

### Prompt Architecture

The action uses a two-layer prompt system for better control and consistency:

1. **System Prompt** (`templates/system-prompt.md`): A minimal, consistent prompt that establishes Claude's role as an AI assistant working in GitHub repositories. This is the same across all modes and is not exposed to end users.

2. **User Prompts** (mode-specific templates):
   - `pr-gen.md` - Detailed instructions for PR generation
   - `pr-update.md` - Structured approach for handling PR feedback
   - `plan-gen.md` - Comprehensive planning framework

This separation ensures:
- Consistent base behavior across all modes
- Full control over instructions without conflicts with base action defaults
- Clear separation between system-level setup and task-specific guidance

Templates use `{{ variable }}` syntax for variable substitution and can be customized to match your organization's specific requirements and coding standards.

## Troubleshooting

### "Authentication required" Error

If you see an authentication error, ensure you have:
- Added `ANTHROPIC_API_KEY` to your repository secrets
- The secret name is exactly `ANTHROPIC_API_KEY` (case-sensitive)
- Your API key is valid and has sufficient credits
- Or configured alternative authentication (Bedrock/Vertex)

### "No changes were made by Claude Code"

This can happen when:
- The prompt was unclear or impossible to implement
- All requested changes already exist
- Claude Code encountered an error during execution
- Check the action logs for more details

### Setup/Dependency Issues

If setup fails:
- Ensure `.devsy/setup.sh` exists and is executable (`chmod +x .devsy/setup.sh`)
- Check that your setup script includes proper error handling (`set -e`)
- Verify that required tools (npm, pip, etc.) are available in the GitHub Actions environment
- Test your setup script locally before committing

## License

This action is built on top of [claude-code-base-action](https://github.com/anthropics/claude-code-base-action) and follows similar patterns to [claude-code-action](https://github.com/anthropics/claude-code-action).

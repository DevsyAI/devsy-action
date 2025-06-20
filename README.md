# Devsy Action

A GitHub Action that leverages Claude Code to automatically generate pull requests, update existing PRs based on feedback, or create implementation plans. Designed to be triggered via `workflow_dispatch` for remote execution with optional callback support.

## Features

- **PR Generation (`pr-gen`)**: Create pull requests from arbitrary prompts
- **PR Updates (`pr-update`)**: Update existing PRs based on review feedback
- **Plan Generation (`plan-gen`)**: Generate detailed implementation plans without making code changes
- **Remote Triggering**: Designed for `workflow_dispatch` to be called programmatically
- **Callback Support**: Optional webhook callback when execution completes

## Quick Setup 

### One-Command Install

Run this in your repository root:

```bash
curl -fsSL https://raw.githubusercontent.com/DevsyAI/devsy-action/main/install-devsy.sh | bash
```

This automatically creates the workflow file and optionally sets up a dependency script.

### Manual Setup (4 Steps)

If you prefer manual setup:

#### Step 1: Copy the Workflow File

Copy `devsy.yml` to `.github/workflows/devsy.yml` in your repository:

```bash
mkdir -p .github/workflows
curl -o .github/workflows/devsy.yml https://raw.githubusercontent.com/DevsyAI/devsy-action/main/devsy.yml
```

Or manually copy the content from [devsy.yml](devsy.yml).

#### Step 2: Configure Repository Settings

Enable GitHub Actions to create pull requests:

1. **Repository Settings**: Go to **Settings** → **Actions** → **General**
2. **Enable PR Creation**: Check ✅ **"Allow GitHub Actions to create and approve pull requests"**
3. **Set Permissions**: Under "Workflow permissions", select **"Read and write permissions"**

> **For Organization Repos**: You must enable this setting at the organization level first, then at the repository level.

#### Step 3: Add Your API Key

Add your Anthropic API key to repository secrets:

1. **Get API Key**: Visit [console.anthropic.com](https://console.anthropic.com)
2. **Add Secret**: Go to **Settings** → **Secrets and variables** → **Actions**
3. **Create**: Click **"New repository secret"**
   - **Name**: `ANTHROPIC_API_KEY`
   - **Value**: Your API key

#### Step 4: Enable Callbacks

To receive completion webhooks, add a callback token:

1. **Generate Token**: Organization admin creates token at [devsy.ai Settings page](https://devsy.ai)
2. **Add Secret**: Go to **Settings** → **Secrets and variables** → **Actions**
3. **Create**: Click **"New repository secret"**
   - **Name**: `DEVSY_ORG_OAUTH_TOKEN`
   - **Value**: Token from devsy.ai Settings page

> This enables secure webhook notifications when Devsy completes tasks.

### Custom Setup Script (Recommended)

For projects with dependencies, create a setup script:

```bash
mkdir -p .devsy
curl -o .devsy/setup.sh https://raw.githubusercontent.com/DevsyAI/devsy-action/main/setup.sh
```

Then edit `.devsy/setup.sh` and uncomment the sections you need (Python, Node.js, etc.).

Finally, configure your workflow to use the setup script:

```yaml
- uses: DevsyAI/devsy-action@main
  with:
    mode: pr-gen
    prompt: "Add new feature"
    setup_script: '.devsy/setup.sh'  # Add this line
    allowed_tools: 'Bash(python:*),Bash(npm:*)'  # Enable tools for your stack
```

This ensures dependencies are installed in the correct Python environment before Claude Code execution.

### Alternative Authentication

Instead of Anthropic API key, you can use:
- **AWS Bedrock**: Set `use_bedrock: true` (requires AWS credentials)
- **Google Vertex**: Set `use_vertex: true` (requires GCP credentials)

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
- `setup_script`: Path to setup script to run before Claude Code execution
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
- Ensure your setup script path is correct in the `setup_script` input
- Verify the setup script exists and is executable (`chmod +x .devsy/setup.sh`)
- Check that your setup script includes proper error handling (`set -e`)
- The setup script runs after Python environment setup but before Claude Code execution
- Test your setup script locally before committing

### "No module named" Errors

If Claude can't find installed packages:
- Use the `setup_script` input instead of running setup in workflow steps
- Always use `python -m pytest` instead of just `pytest` in your instructions
- Ensure dependencies are installed via the setup script, not in earlier workflow steps

## License

This action is built on top of [claude-code-base-action](https://github.com/anthropics/claude-code-base-action) and follows similar patterns to [claude-code-action](https://github.com/anthropics/claude-code-action).

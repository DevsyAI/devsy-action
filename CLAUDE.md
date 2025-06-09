# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**devsy-action** is a GitHub Action that leverages Claude Code to automatically:
- Generate pull requests (PRs) from GitHub issues
- Update existing PRs based on review feedback
- Create detailed implementation plans for complex features

## Project Structure

```
devsy-action/
├── action.yml           # GitHub Action definition with inputs/outputs
├── README.md           # User documentation
├── requirements.txt    # Python dependencies (requests>=2.31.0)
├── scripts/           # Core Python scripts
│   ├── extract_outputs.py      # Extract PR numbers, URLs, and plan content from Claude's output
│   ├── github_token_exchange.py # Exchange GitHub Actions token for devsy-bot GitHub App token
│   └── prepare_prompt.py       # Generate prompts based on action mode and inputs
└── templates/         # Prompt templates for different modes
    ├── README.md              # Template system documentation
    ├── plan-gen.md           # User prompt for plan generation
    ├── pr-gen.md             # User prompt for PR generation
    ├── pr-update.md          # User prompt for PR updates
    ├── system-prompt-plan-gen.md  # System prompt for plan generation
    ├── system-prompt-pr-gen.md    # System prompt for PR generation
    └── system-prompt-pr-update.md # System prompt for PR updates
```

## Key Features

### Action Modes
1. **`pr-gen`**: Generate new pull requests from GitHub issues
2. **`pr-update`**: Update existing PRs based on review feedback
3. **`plan-gen`**: Create implementation plans without code changes

### Authentication
- Primary: Uses GitHub Actions token with devsy-bot fallback
- Fallback: Exchanges token for devsy-bot GitHub App installation token
- Supports custom GitHub App authentication via inputs

### Template System
- Uses Jinja2-style template variables (e.g., `{{ issue_title }}`)
- Supports custom prompts while maintaining default templates
- System prompts establish Claude's role and behavior
- User prompts provide specific task context

## Development Guidelines

### Running Tests
```bash
# Install dependencies
pip install -r requirements.txt

# Run individual scripts for testing
python scripts/prepare_prompt.py --mode pr-gen --issue-title "Test" --issue-body "Test body"
python scripts/github_token_exchange.py --help
python scripts/extract_outputs.py --help
```

### Code Style
- **Python**: Follow PEP 8 conventions
- **Type hints**: Use where beneficial for clarity
- **Error handling**: Always handle API failures gracefully
- **Logging**: Use structured logging for debugging
- **Documentation**: Update README.md for user-facing changes

### Making Changes

#### Adding a New Mode
1. Create new template files in `templates/`:
   - `templates/your-mode.md` (user prompt)
   - `templates/system-prompt-your-mode.md` (system prompt)
2. Update `scripts/prepare_prompt.py` to handle the new mode
3. Update `scripts/extract_outputs.py` if new outputs are needed
4. Update `action.yml` to document the new mode
5. Update README.md with usage examples

#### Modifying Templates
- Templates use Jinja2-style variables: `{{ variable_name }}`
- Available variables depend on the mode:
  - All modes: `issue_title`, `issue_body`, `issue_url`, `issue_number`
  - `pr-update`: Also includes `pr_feedback`
- Keep system prompts focused on Claude's role and capabilities
- Keep user prompts focused on the specific task

#### Updating Script Logic
- `prepare_prompt.py`: Handles prompt generation and template rendering
- `github_token_exchange.py`: Manages GitHub authentication
- `extract_outputs.py`: Parses Claude's output for PR numbers, URLs, and content
- Maintain backward compatibility when possible
- Add clear error messages for validation failures

## API Integration

### GitHub API Usage
- Uses GitHub REST API for token exchange
- Requires appropriate permissions for the repository
- Handles rate limiting and authentication errors

### Claude Code Integration
- Expects Claude Code CLI to be available in the environment
- Uses `--output-format json` for structured output parsing
- Supports all Claude Code CLI flags via `additional_args`

## Security Considerations

- Never log or expose sensitive tokens
- Always validate inputs before using in prompts
- Use GitHub's built-in secret masking for sensitive outputs
- Limit permissions to minimum required for operation

## Common Issues and Solutions

### Authentication Failures
- Ensure GitHub token has appropriate permissions
- Check if devsy-bot is installed on the repository
- Verify custom GitHub App credentials if provided

### Template Rendering Errors
- Check for missing required variables
- Ensure template syntax is valid Jinja2
- Verify custom templates match expected format

### Output Extraction Issues
- Claude Code must use `--output-format json`
- PR numbers must be in format `#123` or `PR #123`
- URLs must be complete GitHub URLs

## Maintenance Notes

- This action is designed to be standalone and portable
- Dependencies are minimal to ensure reliability
- Templates can be customized without modifying code
- All configuration is done through action inputs
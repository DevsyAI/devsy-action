# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**devsy-action** is a GitHub Action that leverages Claude Code to automatically:
- Generate pull requests (PRs) from arbitrary prompts
- Update existing PRs based on review feedback
- Create detailed implementation plans for complex features

The action is designed for remote triggering via `workflow_dispatch` API calls with optional callback support.

## Project Structure

```
devsy-action/
├── action.yml              # GitHub Action definition with inputs/outputs
├── README.md              # User documentation
├── LICENSE                # MIT License
├── requirements.txt       # Python dependencies (requests>=2.31.0, pytest for dev)
├── pytest.ini             # Pytest configuration
├── src/                   # Core Python scripts (all executable)
│   ├── extract_outputs.py         # Extract PR numbers, URLs, and plan content from Claude's output
│   ├── github_token_exchange.py   # Exchange GitHub Actions token for devsy-bot GitHub App token
│   ├── prepare_prompt.py          # Generate prompts based on action mode and inputs
│   ├── prepare_tools.py           # Prepare allowed/disallowed tools configuration
│   ├── send_callback.py           # Send webhook callbacks on completion
│   └── validate_inputs.py         # Validate action inputs based on mode
├── templates/             # Prompt templates for different modes
│   ├── README.md                  # Template system documentation
│   ├── plan-gen.md               # User prompt for plan generation
│   ├── pr-gen.md                 # User prompt for PR generation
│   ├── pr-update.md              # User prompt for PR updates
│   ├── system-prompt-plan-gen.md # System prompt for plan generation
│   ├── system-prompt-pr-gen.md   # System prompt for PR generation
│   └── system-prompt-pr-update.md # System prompt for PR updates
├── tests/                 # Unit tests for all Python scripts
│   ├── test_*.py                 # Comprehensive test coverage (71 tests)
│   └── __init__.py
├── docs/                  # Additional documentation
│   └── TODOS.md                  # Marketplace publishing roadmap
└── .github/workflows/     # CI/CD workflows
    └── ci.yml                    # Run tests and validate action.yml

```

## Key Features

### Action Modes
1. **`pr-gen`**: Generate new pull requests from prompts
2. **`pr-update`**: Update existing PRs based on review feedback  
3. **`plan-gen`**: Create implementation plans without code changes

### Authentication
- Primary: Attempts to exchange GitHub Actions token for devsy-bot access token
- Fallback: Uses standard GitHub Actions bot token if devsy-bot unavailable
- Supports AWS Bedrock and Google Vertex AI as alternatives to Anthropic API
- Custom GitHub App authentication via inputs

### Template System
- Uses Jinja2-style template variables (e.g., `{{ user_prompt }}`)
- Separate system and user prompts for each mode
- Templates can be customized without modifying code
- Variables available depend on the mode

### Tool Configuration
Base tools always included:
- File operations: Edit, Read, Write, Glob, Grep, LS
- Git commands: All git operations via Bash(git:*)
- Search: Ripgrep via Bash(rg:*)
- Task management: Task, TodoWrite, TodoRead
- GitHub integration: mcp__github__create_pull_request

Additional tools can be added via `allowed_tools` input.

## Common Development Tasks

### Running Tests
```bash
# Install all dependencies (including dev)
pip install -r requirements.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_prepare_prompt.py

# Run with verbose output
pytest -v

# Run specific test function
pytest tests/test_prepare_prompt.py::TestPreparePrompt::test_pr_gen_mode
```

### Testing Individual Scripts
```bash
# Test prompt preparation
python src/prepare_prompt.py --mode pr-gen --prompt "Add health check endpoint" --repo owner/repo --github-token $GITHUB_TOKEN

# Test output extraction  
python src/extract_outputs.py --execution-file claude-execution.json --mode pr-gen

# Test tool preparation
python src/prepare_tools.py --allowed-tools "Bash(npm install)" --disallowed-tools "Bash(rm:*)"

# Validate inputs
python src/validate_inputs.py --mode pr-update --pr-number 123 --anthropic-api-key $API_KEY
```

### Linting and Code Quality
Currently no automated linting is configured. Follow PEP 8 conventions manually. Consider adding:
- `black` for code formatting
- `flake8` or `ruff` for linting
- `mypy` for type checking

## High-Level Architecture

### Execution Flow
1. **Input Validation** (`validate_inputs.py`): Validates required inputs based on mode
2. **Token Exchange** (`github_token_exchange.py`): Attempts to get devsy-bot token
3. **Prompt Preparation** (`prepare_prompt.py`): Loads templates, fetches GitHub data, renders prompts
4. **Tool Configuration** (`prepare_tools.py`): Merges base tools with user-specified tools
5. **Claude Code Execution**: Uses anthropics/claude-code-base-action with MCP GitHub server
6. **Output Extraction** (`extract_outputs.py`): Parses Claude's JSON output for PR info
7. **Callback Notification** (`send_callback.py`): Sends webhook if callback_url provided

### Key Design Decisions
- **Modular Python Scripts**: Each script has a single responsibility and can be tested independently
- **Template-Based Prompts**: Prompts are externalized to templates for easy customization
- **Intelligent Authentication**: Gracefully falls back from devsy-bot to GitHub Actions bot
- **Remote Triggering Focus**: Designed for programmatic triggering via workflow_dispatch API
- **Comprehensive Error Handling**: All scripts handle failures gracefully with clear error messages

### GitHub MCP Integration
The action uses Model Context Protocol (MCP) to give Claude Code access to GitHub APIs:
- Configured via `mcp_config` in the base action
- Uses the exchanged token for authentication
- Enables `mcp__github__create_pull_request` tool

## Adding New Features

### Adding a New Mode
1. Create templates in `templates/`:
   - `templates/your-mode.md` (user prompt)  
   - `templates/system-prompt-your-mode.md` (system prompt)
2. Update `src/prepare_prompt.py`:
   - Add case in main() for the new mode
   - Create prepare function like `prepare_your_mode_prompt()`
3. Update `src/validate_inputs.py`:
   - Add validation logic for the new mode
4. Update `src/extract_outputs.py` if new outputs needed:
   - Add extraction logic for mode-specific outputs
5. Update `action.yml`:
   - Document the new mode in mode input description
   - Add any new outputs
6. Add tests for the new mode in all affected test files
7. Update README.md with usage examples

### Modifying Templates  
- Templates use `{{ variable }}` syntax
- Variables are replaced using simple string replacement (not full Jinja2)
- Available variables by mode:
  - All modes: `user_prompt`, `custom_instructions`, `repo_name`
  - pr-gen: `base_branch`
  - pr-update: `pr_number`, `pr_title`, `pr_body`, `comments_text`, `additional_instructions`
  - plan-gen: No additional variables
- Test template changes by running the prepare_prompt.py script directly

## Testing Strategy

### Unit Tests
- Located in `tests/` directory
- Use pytest with pytest-mock for mocking
- Cover all main functions and error cases
- Run automatically in CI on push/PR

### Manual Testing
For end-to-end testing:
1. Create a test workflow in `.github/workflows/test-devsy.yml`
2. Trigger via GitHub UI or API
3. Verify outputs and callback functionality

### CI/CD
- `.github/workflows/ci.yml` runs on all pushes and PRs
- Validates Python syntax
- Runs all unit tests
- Validates action.yml structure

## Security Considerations

- **Token Handling**: Tokens are never logged; GitHub masks them automatically
- **Input Validation**: All inputs are validated before use
- **Callback Security**: Supports custom auth headers for webhook callbacks
- **Template Injection**: Templates use simple string replacement, not eval
- **Permission Scope**: Action only requests necessary permissions

## Troubleshooting

### Common Issues

1. **Token Exchange Fails**
   - Check if devsy-bot is installed on the repository
   - Verify the backend_url is accessible
   - Action will fall back to GitHub Actions token automatically

2. **Template Not Found**
   - Ensure template files exist in templates/ directory
   - Check file naming matches the mode name

3. **Output Extraction Fails**
   - Verify Claude Code is using `--output-format json`
   - Check execution file contains valid JSON
   - PR numbers must be in format `#123` or `PR #123`

4. **Callback Fails**
   - Verify callback_url is accessible
   - Check auth token/header configuration
   - Review callback payload in logs

### Debug Mode
To debug issues:
1. Check GitHub Actions logs for detailed output
2. Download the execution file artifact
3. Run scripts locally with test data
4. Add print statements to scripts (they'll appear in logs)

## Future Improvements

See `docs/TODOS.md` for planned enhancements including:
- Python linting and type checking
- Integration tests  
- Enhanced error handling with retries
- Dependabot configuration
- Security audit
- Documentation improvements
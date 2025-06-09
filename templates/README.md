# Prompt Templates

This directory contains the prompt templates used by the Devsy Action for different modes.

## Template Files

- `pr-gen.md` - Template for PR generation mode
- `pr-update.md` - Template for PR update mode
- `plan-gen.md` - Template for plan generation mode

## Template Syntax

Templates use simple `{{ variable }}` syntax for variable substitution:

- `{{ user_prompt }}` - The user's input prompt
- `{{ custom_instructions }}` - Additional custom instructions
- `{{ pr_number }}` - Pull request number (pr-update only)
- `{{ pr_title }}` - Pull request title (pr-update only)
- `{{ pr_body }}` - Pull request description (pr-update only)
- `{{ comments_text }}` - Recent PR comments (pr-update only)
- `{{ additional_instructions }}` - Additional update instructions (pr-update only)

## Editing Templates

To modify the prompts, simply edit the markdown files in this directory. The changes will be automatically picked up by the action.

Keep the templates clear and focused on the specific task for each mode.

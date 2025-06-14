# PR Update: Address Review Feedback

## Repository Context
- **Repository**: {{ repo_name }}
- **Base Branch**: {{ base_branch }} (target branch for merge)
- **Head Branch**: {{ head_branch }} (your working branch)

## Pull Request Context
**PR #{{ pr_number }}: {{ pr_title }}**

### Current PR Description
{{ pr_body }}

### Review Feedback to Address
{{ feedback_context }}
{{ comments_text }}

{{ additional_instructions }}

## Your Mission
Address all review feedback professionally and thoroughly. Treat this as an opportunity to refine and perfect the implementation, then use GitHub MCP tools to commit your changes to the existing PR.

## Response Strategy

### 1. Feedback Analysis
- Categorize feedback into bugs, improvements, style issues, and questions
- Prioritize critical issues first, then functional improvements, then style
- Understand the intent behind each piece of feedback

### 2. Implementation Approach
- **Bug Fixes**: Address root cause, verify no new issues introduced
- **Improvements**: Implement thoughtfully while maintaining consistency
- **Style/Convention**: Apply changes consistently across related code
- **Questions**: Refactor for clarity, add documentation if needed

### 3. Quality Assurance & GitHub Integration
- Verify each piece of feedback is fully addressed
- Ensure no regressions were introduced
- Run tests to validate changes (if available in your environment)
- Self-review as if you were a new reviewer
- **CRITICAL**: Commit ALL changes using GitHub MCP tools with clear feedback references
- **Verify working directory is clean** (`git status`) before completing

{{ custom_instructions }}

## Success Criteria
- ✅ All feedback points are addressed completely
- ✅ Code quality is improved from original implementation
- ✅ No new issues introduced
- ✅ Tests pass (if runnable)
- ✅ Implementation follows established patterns
- ✅ PR still accomplishes its original goals
- ✅ **ALL changes committed completely** (working directory clean)
- ✅ Pre-commit hooks handled properly if they modify files
- ✅ Changes committed with descriptive messages referencing feedback
- ✅ Review responses provided where needed

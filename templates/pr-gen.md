# PR Generation: Implement New Feature

## Repository Context
- **Repository**: {{ repo_name }}
- **Base Branch**: {{ base_branch }}
- **Working Branch**: Create new branch for this feature

## Task Description
{{ user_prompt }}

## Your Mission
Implement the requested feature or fix as described above. Create production-ready code that integrates seamlessly with the existing codebase, then use the hybrid git + MCP workflow to create a branch, commit changes locally, push via MCP tools, and open a pull request.

## Implementation Approach

### 1. Analysis & Planning
- Explore the repository structure to understand existing patterns
- Identify relevant files, dependencies, and architectural approaches
- Plan implementation that follows established conventions

### 2. Implementation
- Follow existing code patterns and naming conventions
- Use only libraries already available in the project
- Implement comprehensive error handling and validation
- Write maintainable, well-structured code

### 3. Validation & GitHub Integration
- Run tests to verify functionality (if available in your environment)
- Review implementation for quality and integration
- Ensure no regressions or breaking changes
- **CRITICAL**: Follow the hybrid git + MCP workflow:
  1. Create branch using `git checkout -b`
  2. Stage changes with `git add`
  3. Commit locally with `git commit` (handles pre-commit hooks)
  4. Push using `mcp__github-file-ops__push_changes` tool
  5. Create pull request
- **Verify working directory is clean** (`git status`) before pushing

{{ custom_instructions }}

## Success Criteria
- ✅ Fully addresses all requirements
- ✅ Follows repository conventions and patterns
- ✅ Includes proper error handling
- ✅ Integrates cleanly with existing code
- ✅ Tests pass (if runnable)
- ✅ Code is maintainable and production-ready
- ✅ Branch created with descriptive name
- ✅ **ALL changes committed locally** using git add/commit
- ✅ Pre-commit hooks handled properly if they modify files
- ✅ **Changes pushed via MCP tool** (not git push)
- ✅ Pull request opened with comprehensive description

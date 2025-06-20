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
- **CRITICAL**: Follow git workflow with MCP push:
  1. Create branch, stage changes, commit locally
  2. Push using `mcp__github-file-ops__push_changes` tool
  3. Create pull request
- Verify clean working directory before pushing

{{ custom_instructions }}

## Success Criteria
- ✅ Fully addresses all requirements
- ✅ Follows repository conventions and patterns
- ✅ Includes proper error handling
- ✅ Integrates cleanly with existing code
- ✅ Tests pass (if runnable)
- ✅ Code is maintainable and production-ready
- ✅ Branch created with descriptive name
- ✅ **Changes committed locally and pushed via MCP tool**
- ✅ Pull request opened with comprehensive description

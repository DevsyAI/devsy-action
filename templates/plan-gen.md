# Plan Generation: Create Implementation Roadmap

## Repository Context
- **Repository**: {{ repo_name }}
- **Base Branch**: {{ base_branch }}
- **Analysis Scope**: Use GitHub MCP tools to understand current codebase

## Task Context
{{ user_prompt }}

## Your Mission
Create a comprehensive, actionable implementation plan that guides successful completion of this task. The plan should be specific, practical, and ready for execution. Use GitHub MCP tools to analyze the repository and provide concrete, context-aware recommendations.

## Required Plan Structure

### 1. Task Analysis
- **Objective**: Clear statement of what needs to be accomplished
- **Requirements**: Explicit and implicit requirements from the prompt
- **Success Criteria**: Measurable outcomes indicating completion
- **Scope Boundaries**: What is and isn't included

### 2. Technical Approach
- **Architecture Overview**: High-level design decisions and rationale
- **Technology Stack**: Specific libraries, frameworks, or tools to use
- **Integration Points**: How this fits with existing systems
- **Design Patterns**: Relevant patterns to apply

### 3. Implementation Roadmap
Break down into logical phases with specific deliverables:
- **Phase 1: Foundation** - Setup and infrastructure
- **Phase 2: Core Features** - Primary functionality
- **Phase 3: Integration** - System connections
- **Phase 4: Validation** - Testing and refinement

For each phase: files to modify, functions to implement, dependencies needed

### 4. Code Architecture
```
project-structure/
├── [relevant directories]
└── [files to create/modify with purpose]
```

### 5. Risk Assessment
| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|-------------------|
| [Key risks] | H/M/L | H/M/L | [Specific strategies] |

### 6. Testing Strategy
- **Unit Tests**: Key components requiring coverage
- **Integration Tests**: Critical interaction points
- **Edge Cases**: Specific scenarios to validate

### 7. Implementation Checklist
- [ ] Environment and dependencies ready
- [ ] Core functionality implemented
- [ ] Integration points working
- [ ] Tests passing (if available)
- [ ] Documentation updated

{{ custom_instructions }}

## Output Format
Please provide your complete implementation plan between the delimiter blocks:

=== START OF PLAN MARKDOWN ===
[Your complete implementation plan following the structure above]
=== END OF PLAN MARKDOWN ===

## Quality Standards
- Be specific and actionable with concrete examples
- Reference existing codebase patterns where applicable
- Consider security, performance, and maintainability
- Ensure plan is self-contained and executable

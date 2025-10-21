<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles:
  * I. GitHub Workflow Discipline - EXPANDED with mandatory requirements:
    - Added ABSOLUTE RULE: NO WORK WITHOUT A GITHUB ISSUE
    - Added PROHIBITION: Code changes without issue are STRICTLY FORBIDDEN
    - Added Branch Cleanup MANDATORY section with specific git commands
    - Added Workflow Completion requirement before starting new work
- Added sections:
  * Issue Closure and Branch Cleanup (expanded subsection of Principle I)
- Removed sections: N/A
- Templates requiring updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section compatible
  ✅ .specify/templates/spec-template.md - Requirements section compatible
  ✅ .specify/templates/tasks-template.md - Testing gates compatible
  ⚠️ .specify/templates/commands/*.md - Commands should verify issue existence before work
  ⚠️ README.md or quickstart docs - Should document branch cleanup workflow
- Follow-up TODOs:
  * Consider adding pre-commit hook to verify current branch links to a GitHub issue
  * Consider adding GitHub Actions automation for branch deletion after PR merge
-->

# F5 XC CE Terraform Constitution

## Core Principles

### I. GitHub Workflow Discipline (NON-NEGOTIABLE)

**ABSOLUTE RULE: NO WORK WITHOUT A GITHUB ISSUE. All code modifications MUST follow the complete GitHub workflow:**

- **Issue Creation REQUIRED (PRE-REQUISITE)**: Before ANY code change, modification, or implementation work begins, a GitHub issue MUST be created describing:
  - The problem or feature request
  - Expected behavior and success criteria
  - Acceptance criteria for completion
  - Labels for categorization (bug, feature, enhancement, etc.)
  - **PROHIBITION**: Writing code, creating branches, or making any changes WITHOUT an issue is STRICTLY FORBIDDEN

- **Branch Strategy MANDATORY**: All work MUST occur in feature branches:
  - Branch naming: `[issue-number]-brief-description` (e.g., `42-add-logging`)
  - NEVER commit directly to `main` or `master`
  - Create branch from latest `main` before starting work
  - Branch MUST be linked to the GitHub issue

- **Pull Request REQUIRED**: All changes MUST go through pull requests:
  - PR title MUST reference issue: "Fixes #42: Add logging to auth module"
  - PR description MUST link to issue and describe changes
  - PR MUST pass all automated checks before merge
  - At least one approval REQUIRED before merge (if team size permits)

- **Issue Closure and Branch Cleanup**: After PR merge, the following MUST occur:
  - Issue MUST be closed ONLY when:
    - PR is merged to main branch
    - All acceptance criteria are met
    - Tests pass and code is deployed/validated
  - **Branch Deletion MANDATORY**:
    - Local feature branch MUST be deleted: `git branch -d [branch-name]`
    - Remote feature branch MUST be deleted: `git push origin --delete [branch-name]`
    - Git client MUST switch back to main: `git checkout main`
    - Main branch MUST be updated: `git pull origin main`
  - **Workflow Completion**: The cycle Issue → Branch → PR → Merge → Cleanup MUST be fully completed before starting new work

**Rationale**: This workflow ensures traceability, enables collaboration, maintains project history, prevents untracked changes from entering the codebase, and keeps the repository clean by removing obsolete branches. The mandatory issue requirement prevents ad-hoc, undocumented changes that bypass quality gates and review processes.

### II. Code Quality Standards

**All code MUST meet the following quality gates before merge:**

- **Pre-commit Hooks (NON-NEGOTIABLE)**: MANDATORY validation executed before EVERY commit
  - **Framework Required**: MUST use pre-commit framework (https://pre-commit.com)
  - **Configuration File**: `.pre-commit-config.yaml` MUST be present in repository root
  - **Installation Required**: ALL developers MUST install pre-commit hooks via `pre-commit install`
  - **Comprehensive Coverage**: Hooks MUST validate ALL file types in repository:
    - Terraform files (.tf, .tfvars): terraform_fmt, terraform_validate, terraform_docs, tflint
    - YAML files (.yml, .yaml): yamllint, check-yaml
    - JSON files (.json): check-json, prettier
    - Markdown files (.md): markdownlint, prettier
    - Shell scripts (.sh): shellcheck, shfmt
    - Python files (.py): ruff, black (check-only), mypy
    - Go files (.go): gofmt, golangci-lint
    - General: trailing-whitespace, end-of-file-fixer, check-merge-conflict, detect-secrets

  - **READ-ONLY VALIDATION (CRITICAL)**: Pre-commit hooks MUST ONLY validate and report errors
    - **NO AUTO-FIX**: Hooks MUST NOT automatically fix or correct any problems
    - **Display Errors Only**: Hooks MUST display validation errors and exit with non-zero status
    - **Manual Fixes Required**: Developers MUST manually fix all reported errors
    - **Configuration Enforcement**:
      - Terraform: `terraform fmt -check` (NOT `terraform fmt -write`)
      - Black: `black --check --diff` (NOT `black`)
      - Prettier: `prettier --check` (NOT `prettier --write`)
      - All formatters: Use check/diff modes, NEVER write modes

  - **BYPASS FORBIDDEN (NON-NEGOTIABLE)**: Bypassing pre-commit checks is STRICTLY PROHIBITED
    - **No --no-verify**: `git commit --no-verify` is FORBIDDEN
    - **No Commenting Out**: Commenting out or disabling pre-commit checks is FORBIDDEN
    - **No Skip Flags**: Using `SKIP=` environment variable is FORBIDDEN
    - **Enforcement**: CI/CD pipeline MUST run identical checks to prevent bypass
    - **Code Review**: Reviewers MUST reject any PR attempting to bypass or disable checks
    - **Exception Process**: If a hook genuinely needs to be skipped (e.g., emergency hotfix):
      1. MUST be documented in PR description with detailed justification
      2. MUST be approved by technical lead
      3. MUST create follow-up issue to fix violations
      4. MUST be limited to emergency situations only

  - **Hook Execution Order**: Hooks MUST run in logical dependency order
    1. File-level checks (trailing-whitespace, end-of-file-fixer, mixed-line-ending)
    2. Syntax validation (check-yaml, check-json, terraform_validate)
    3. Security checks (detect-secrets, checkov security scans)
    4. Linting (yamllint, shellcheck, tflint, markdownlint)
    5. Formatting validation (terraform fmt -check, black --check, prettier --check)
    6. Documentation generation checks (terraform_docs)

  - **Performance Requirements**: Pre-commit hooks MUST complete in reasonable time
    - Individual hooks: <30 seconds per file type
    - Total pre-commit time: <2 minutes for typical commit
    - Hooks MUST run only on staged files (not entire repository)
    - Parallel execution MUST be enabled where possible

  - **Error Reporting**: Hook failures MUST provide actionable error messages
    - Clear indication of which file(s) failed validation
    - Specific line numbers and error descriptions
    - Suggested fix commands or documentation links
    - Exit with non-zero status to block commit

- **Linting**: Code MUST pass all configured linters without warnings
  - Configuration files MUST be present in repository root
  - Linting MUST run automatically in CI/CD pipeline
  - No lint rule exceptions without documented justification

- **Code Review**: All code MUST be reviewed before merge
  - Reviewers MUST verify adherence to this constitution
  - Reviews MUST check for security vulnerabilities
  - Reviews MUST validate test coverage
  - Code style MUST be consistent with existing patterns

- **Documentation**: Code MUST be self-documenting and include:
  - Clear function/module/class documentation
  - Complex logic MUST have inline comments explaining "why"
  - Public APIs MUST have usage examples
  - README updates for new features or changed behavior

- **Security**: Code MUST follow security best practices
  - No hardcoded secrets or credentials
  - Input validation on all external data
  - Proper error handling without exposing sensitive information
  - Dependencies MUST be kept up to date

**Rationale**: Quality gates prevent technical debt accumulation, reduce bugs, improve maintainability, and ensure professional code standards. Pre-commit hooks enforce standards at the earliest possible point (before commit), preventing quality issues from entering version control and ensuring consistent code quality across all contributors.

### III. Testing Standards (NON-NEGOTIABLE)

**Test-Driven Development (TDD) is MANDATORY for all new features:**

- **Tests Written First**: For new features:
  1. Write tests that describe expected behavior
  2. Get user/stakeholder approval on test scenarios
  3. Verify tests FAIL (red phase)
  4. Implement feature until tests PASS (green phase)
  5. Refactor while maintaining passing tests

- **Test Coverage Requirements**:
  - **Unit Tests**: REQUIRED for all business logic functions
    - Each function MUST have tests for: happy path, edge cases, error conditions
    - Minimum 80% code coverage for new code
  - **Integration Tests**: REQUIRED for:
    - Cross-module interactions
    - External service integrations
    - Database operations
    - API endpoint behaviors
  - **Contract Tests**: REQUIRED for:
    - Public API changes
    - Inter-service communication
    - Shared data schemas

- **Test Quality Standards**:
  - Tests MUST be deterministic (no flaky tests)
  - Tests MUST run in isolation (no dependencies between tests)
  - Tests MUST be fast (<1s per unit test, <10s per integration test)
  - Tests MUST have clear Given-When-Then structure
  - Test names MUST clearly describe what is being tested

- **Regression Protection**:
  - Bug fixes MUST include tests that would have caught the bug
  - Tests MUST continue to pass after merge

**Rationale**: TDD ensures features are testable, prevents regressions, improves design quality, and provides living documentation of expected behavior.

### IV. User Experience Consistency

**All user-facing changes MUST maintain consistent experience:**

- **Interface Consistency**:
  - UI components MUST follow established design patterns
  - Error messages MUST be clear, actionable, and consistent in tone
  - Terminology MUST be consistent across all interfaces
  - User flows MUST be intuitive and predictable

- **Performance Experience**:
  - User actions MUST receive immediate feedback (loading states, progress indicators)
  - Operations taking >2 seconds MUST show progress
  - Error states MUST provide recovery paths
  - Timeouts MUST be reasonable and documented

- **Accessibility**:
  - All interfaces MUST be keyboard navigable
  - Color contrast MUST meet WCAG AA standards
  - Screen reader compatibility MUST be tested
  - Error messages MUST be programmatically associated with inputs

- **Documentation Experience**:
  - User documentation MUST be updated with interface changes
  - Examples MUST be complete and runnable
  - Error messages MUST link to troubleshooting documentation where appropriate

**Rationale**: Consistent UX reduces cognitive load, improves user satisfaction, reduces support burden, and maintains professional product quality.

### V. Performance Requirements

**All code MUST meet performance benchmarks before merge:**

- **Response Time Standards**:
  - API endpoints: <200ms p95 latency for simple operations
  - Database queries: <100ms p95 for read operations
  - UI rendering: <100ms time to interactive for page loads
  - Background jobs: MUST complete within documented SLA

- **Resource Efficiency**:
  - Memory usage MUST not grow unbounded (no memory leaks)
  - CPU usage MUST be proportional to workload
  - Database connections MUST be properly pooled and released
  - File handles MUST be properly closed

- **Scalability**:
  - System MUST handle expected concurrent users (documented in plan.md)
  - Database queries MUST use appropriate indexes
  - N+1 query problems MUST be avoided
  - Caching MUST be used for expensive operations

- **Monitoring Required**:
  - Performance metrics MUST be collected and monitored
  - Alerts MUST be configured for performance degradation
  - Performance tests MUST be part of CI/CD pipeline
  - Regression in performance MUST block deployment

- **Performance Testing**:
  - Load tests REQUIRED for API changes
  - Benchmark tests REQUIRED for critical paths
  - Performance regression tests REQUIRED in CI
  - Performance test results MUST be documented in PRs

**Rationale**: Performance is a feature, not an afterthought. Poor performance degrades user experience, increases infrastructure costs, and limits scalability.

## GitHub Workflow

### Issue Management

**All work MUST originate from a GitHub issue:**

- Issues MUST use appropriate templates (bug, feature, enhancement)
- Issues MUST have clear acceptance criteria
- Issues MUST be labeled for categorization and prioritization
- Issues MUST be assigned before work begins
- Issues MUST be linked to project milestones when applicable

### Branch Management

**Feature branches MUST follow these conventions:**

- **Branch Creation**: Branch from latest `main` before starting work (`git checkout -b [issue-number]-description`)
- **Branch Naming**: `[issue-number]-kebab-case-description` (e.g., `42-add-logging`)
- **Branch Lifecycle**: Keep branches short-lived (<5 days of work)
- **Conflict Prevention**: Rebase on `main` regularly to avoid merge conflicts
- **Branch Cleanup (MANDATORY)**: After PR merge, MUST execute:
  1. Switch to main: `git checkout main`
  2. Update main: `git pull origin main`
  3. Delete local branch: `git branch -d [branch-name]`
  4. Delete remote branch: `git push origin --delete [branch-name]`
- **Verification**: Confirm branch deletion with `git branch -a` (should not show deleted branch)

### Pull Request Standards

**All PRs MUST include:**

- **Title**: "Fixes #[issue]: Brief description"
- **Description**:
  - Link to issue
  - Summary of changes
  - Testing performed
  - Screenshots for UI changes
  - Performance impact notes
- **Checklist**:
  - [ ] Tests added and passing
  - [ ] Documentation updated
  - [ ] No linting errors
  - [ ] Performance validated
  - [ ] Security reviewed

### Merge Strategy

- **Squash merges** preferred for feature branches
- **Merge commits** for important integration points
- **No force pushes** to `main` or shared branches
- All checks MUST pass before merge

## Quality Standards

### Code Review Process

**Every PR MUST be reviewed using this checklist:**

1. **Constitution Compliance**:
   - [ ] GitHub workflow followed (issue → branch → PR)
   - [ ] Tests written and passing
   - [ ] Code quality standards met
   - [ ] Performance requirements validated
   - [ ] UX consistency maintained

2. **Technical Quality**:
   - [ ] Code is readable and maintainable
   - [ ] Logic is sound and efficient
   - [ ] Error handling is comprehensive
   - [ ] No obvious security vulnerabilities

3. **Testing Quality**:
   - [ ] Tests cover happy paths and edge cases
   - [ ] Tests are deterministic and fast
   - [ ] Integration points are tested
   - [ ] Test names clearly describe scenarios

4. **Documentation Quality**:
   - [ ] Code is self-documenting
   - [ ] Complex logic is explained
   - [ ] Public APIs have examples
   - [ ] User docs updated if needed

### Continuous Integration

**CI pipeline MUST enforce:**

- All linters pass with zero warnings
- All tests pass with minimum coverage thresholds
- Performance benchmarks meet requirements
- Security scans show no critical vulnerabilities
- Build succeeds on all target platforms

### Definition of Done

**A task is only "done" when:**

1. Code is written and reviewed
2. All tests pass (unit, integration, contract)
3. Performance validated against requirements
4. Documentation updated
5. PR merged to main
6. Issue closed with verification comment
7. Changes deployed (if applicable)
8. Stakeholders notified

## Governance

### Constitution Authority

This constitution supersedes all other development practices and guidelines. When conflicts arise, this document takes precedence.

### Amendment Process

**Constitution changes MUST follow this process:**

1. **Proposal**: Create GitHub issue with proposed amendment
2. **Discussion**: Allow minimum 5 business days for team feedback
3. **Documentation**: Update constitution with clear rationale
4. **Version Update**: Increment version following semantic versioning:
   - **MAJOR**: Backward-incompatible changes to core principles
   - **MINOR**: New principles or material expansions
   - **PATCH**: Clarifications, wording improvements, typo fixes
5. **Migration Plan**: Document how existing code will be brought into compliance
6. **Approval**: Requires team consensus or designated authority approval
7. **Communication**: Announce changes to all stakeholders

### Compliance Review

**Ongoing compliance enforcement:**

- All PRs MUST verify constitution compliance
- Monthly audits of code quality and test coverage
- Quarterly review of constitution effectiveness
- Annual complete constitution review and update

### Complexity Justification

**Violations of these principles MUST be justified:**

- Documented in plan.md Complexity Tracking table
- Approved by technical lead or team consensus
- Time-boxed with plan to remove exception
- Tracked in technical debt backlog

### Exceptions

**Emergency exceptions MAY be granted when:**

- Production incident requires immediate hotfix
- Security vulnerability requires urgent patching

**Exception process:**
1. Document exception reason in PR
2. Create follow-up issue to properly address
3. Fast-track review with designated approver
4. Return to normal workflow for follow-up work

### Tools and Automation

Refer to `.specify/templates/` for:
- `plan-template.md`: Implementation planning workflow
- `spec-template.md`: Feature specification format
- `tasks-template.md`: Task breakdown and organization
- `checklist-template.md`: Quality gate checklists

**Version**: 1.1.0 | **Ratified**: 2025-10-21 | **Last Amended**: 2025-10-21

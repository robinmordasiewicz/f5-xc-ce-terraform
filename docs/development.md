# Developer Guide

This guide covers development environment setup, code quality standards, and local testing workflows for contributing to the f5-xc-ce-terraform project.

## Table of Contents

- [Developer Environment Setup](#developer-environment-setup)
- [Pre-commit Hooks](#pre-commit-hooks-mandatory)
- [Local Testing](#local-testing)
- [CI/CD Workflows](#cicd-workflows)
- [Project Structure](#project-structure)

## Developer Environment Setup

**IMPORTANT**: All developers MUST set up pre-commit hooks before contributing.

### One-Time Setup

```bash
# Install pre-commit framework and hooks
./scripts/setup-dev-environment.sh
```

This script installs:
- Pre-commit framework
- All code quality tools (linters, formatters, security scanners)
- Git hooks for automatic validation

### Prerequisites

- Terraform >= 1.6.0
- Azure CLI >= 2.45.0
- Go >= 1.21 (for integration tests)
- Python >= 3.11 (for pre-commit framework)

## Pre-commit Hooks (MANDATORY)

Pre-commit hooks validate ALL code changes **before** they enter version control. This is a **NON-NEGOTIABLE** requirement per project constitution.

### Why Pre-commit Hooks?

- **Catch Issues Early**: Validate code before commit, not after PR
- **Consistent Quality**: All contributors use the same validation tools
- **Constitution Compliance**: Enforce code quality standards automatically
- **Fast Feedback**: Get immediate feedback on code quality issues

### Validation Coverage

All file types are validated:

| File Type | Checks Performed |
|-----------|------------------|
| **Terraform** | Format check, syntax validation, documentation, tflint, checkov security |
| **YAML** | yamllint, syntax validation |
| **JSON** | Syntax validation, formatting check |
| **Markdown** | markdownlint, formatting check |
| **Shell** | shellcheck, shfmt format check |
| **Python** | ruff linter, black format check, mypy type checking |
| **Go** | gofmt check, golangci-lint |
| **Security** | detect-secrets, checkov scans |
| **General** | Trailing whitespace, line endings, merge conflicts, large files |

### CRITICAL: Read-Only Validation

**Pre-commit hooks are configured in CHECK-ONLY mode:**

- ❌ Hooks **DO NOT** automatically fix problems
- ✅ Hooks **ONLY** display validation errors
- ✅ Developers **MUST** manually fix all issues
- ⚠️ Bypassing hooks is **STRICTLY FORBIDDEN**

**Examples:**
```bash
# ❌ WRONG - Auto-fixes issues (disabled)
terraform fmt file.tf

# ✅ RIGHT - Check-only mode (enabled)
terraform fmt -check file.tf  # Used by pre-commit

# ❌ FORBIDDEN - Bypassing hooks is prohibited
git commit --no-verify  # Constitution violation!
```

### Using Pre-commit Hooks

Pre-commit hooks run **automatically** on every `git commit`:

```bash
# Normal workflow - hooks run automatically
git add terraform/main.tf
git commit -m "Add load balancer configuration"
# ↳ Pre-commit hooks validate all staged files
# ↳ If validation fails, commit is blocked
# ↳ Fix errors manually and commit again
```

**Manual execution:**
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run terraform-fmt --all-files
pre-commit run detect-secrets --all-files

# Update hook versions
pre-commit autoupdate
```

### Fixing Validation Errors

When pre-commit blocks a commit:

1. **Read the error message carefully** - it shows which file(s) failed and why
2. **Fix the issues manually** - edit files to resolve validation errors
3. **Stage the fixes**: `git add <files>`
4. **Commit again**: `git commit`

**Example workflow:**
```bash
$ git commit -m "Add terraform config"
Check Terraform formatting.................................Failed
- hook id: terraform_fmt
- exit code: 1

terraform/main.tf
--- a/terraform/main.tf
+++ b/terraform/main.tf
@@ -5,7 +5,7 @@
 resource "azurerm_resource_group" "main" {
-  name     =    "my-rg"  # Too much whitespace
+  name     = "my-rg"
   location = "eastus"
 }

# Fix the formatting manually
$ terraform fmt terraform/main.tf
$ git add terraform/main.tf
$ git commit -m "Add terraform config"
✅ All checks passed!
```

### Common Pre-commit Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `terraform fmt failed` | Inconsistent formatting | Run `terraform fmt <file>` |
| `yamllint failed` | YAML style violations | Check `.yamllint` rules, fix manually |
| `detect-secrets failed` | Hardcoded secrets detected | Remove secrets, use environment variables |
| `trailing-whitespace` | Lines end with whitespace | Remove trailing spaces |
| `end-of-file-fixer` | Missing newline at EOF | Add newline at end of file |
| `shellcheck failed` | Shell script issues | Fix per shellcheck suggestions |

### Bypass Prevention

**Constitution Requirement: Bypassing pre-commit checks is STRICTLY PROHIBITED**

❌ **FORBIDDEN Actions:**
- `git commit --no-verify` - Skips all pre-commit hooks
- `SKIP=hook-name git commit` - Skips specific hooks
- Commenting out hooks in `.pre-commit-config.yaml`
- Disabling hooks in git config

✅ **Exception Process (Emergency Only):**
1. Document justification in PR description
2. Obtain technical lead approval
3. Create follow-up issue to fix violations
4. Limited to production incidents or security hotfixes

**CI/CD Enforcement:**
GitHub Actions runs **identical** validation checks to prevent bypass:
- All PRs are validated with same hooks
- Bypassed commits will fail CI/CD
- Reviewers will reject PRs attempting to bypass hooks

## Local Testing

### Pre-commit Validation

```bash
# Run all pre-commit checks manually
pre-commit run --all-files
```

### Terraform Testing

```bash
# Format Terraform code (after fixing pre-commit errors)
terraform fmt -recursive

# Validate configuration
terraform -chdir=terraform/environments/dev validate

# Run tflint
tflint
```

### YAML/Markdown Validation

```bash
# YAML linting
yamllint .github/workflows/

# Markdown linting
markdownlint-cli2 "**/*.md"
```

### Integration Tests

```bash
# Run Go integration tests
cd tests/integration && go test -v ./...
```

### Security Scanning

```bash
# Run checkov security scans
checkov -d terraform/

# Detect secrets
detect-secrets scan
```

## CI/CD Workflows

The project uses GitHub Actions for automated CI/CD:

### terraform-plan.yml
- **Trigger**: Pull requests to main branch
- **Purpose**: Validates Terraform configuration and generates plan
- **Checks**:
  - Terraform format validation
  - Terraform syntax validation
  - Security scanning with checkov
  - Generate and display plan

### terraform-apply.yml
- **Trigger**: Push to main branch (after PR merge)
- **Purpose**: Deploys infrastructure changes to Azure
- **Steps**:
  - Authenticate with Azure using workload identity
  - Initialize Terraform with remote state
  - Apply infrastructure changes
  - Output deployment details

### terraform-destroy.yml
- **Trigger**: Manual workflow dispatch
- **Purpose**: Decommissions infrastructure when needed
- **Safety**: Requires explicit approval before execution

## Project Structure

```
├── .github/workflows/      # GitHub Actions CI/CD pipelines
│   ├── terraform-plan.yml
│   ├── terraform-apply.yml
│   └── terraform-destroy.yml
├── terraform/
│   ├── environments/       # Dev/prod environment configurations
│   │   └── dev/
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   ├── modules/            # Reusable Terraform modules
│   │   ├── azure-hub-vnet/
│   │   ├── azure-spoke-vnet/
│   │   ├── azure-load-balancer/
│   │   ├── f5-xc-registration/
│   │   ├── f5-xc-ce-appstack/
│   │   └── f5-xc-ce-k8s/
│   └── backend.tf          # Remote state configuration
├── tests/
│   ├── integration/        # Go integration tests
│   └── policies/           # OPA policies for validation
├── scripts/
│   ├── setup-backend.sh           # Azure backend setup
│   ├── setup-dev-environment.sh   # Developer environment setup
│   └── verify-issue-context.sh    # Issue validation script
├── docs/                   # Documentation
│   ├── architecture.md     # Technical architecture
│   ├── development.md      # This file
│   └── requirements.md     # System requirements
└── specs/                  # Project specifications
    └── 001-ce-cicd-automation/
```

## Development Workflow

### Standard Feature Development

1. **Create Issue**: Create GitHub issue describing feature/fix
2. **Create Branch**: `git checkout -b [issue-number]-description`
3. **Verify Context**: `./scripts/verify-issue-context.sh`
4. **Develop**: Make changes following code standards
5. **Test Locally**: Run pre-commit and integration tests
6. **Commit**: Pre-commit hooks validate automatically
7. **Push**: `git push origin [branch-name]`
8. **Create PR**: Open pull request with issue reference
9. **CI/CD Validation**: GitHub Actions runs all checks
10. **Review**: Address reviewer feedback
11. **Merge**: Merge to main triggers deployment

### Emergency Hotfix Workflow

1. **Create Issue**: Document emergency with severity
2. **Fast Track Branch**: Create from main with hotfix prefix
3. **Minimal Changes**: Only fix the critical issue
4. **Expedited Review**: Technical lead review
5. **Immediate Deploy**: Merge triggers automated deployment
6. **Follow-up**: Create issues for any bypassed quality checks

## Code Style Guidelines

### Terraform

- Use `terraform fmt` for consistent formatting
- Follow [HashiCorp Style Guide](https://www.terraform.io/docs/language/syntax/style.html)
- Document all modules with README.md
- Use meaningful resource names
- Add comments for complex logic

### YAML

- Use 2-space indentation
- Follow `.yamllint` configuration
- No trailing whitespace
- Explicit `true`/`false` (not `yes`/`no`)

### Shell Scripts

- Use `#!/usr/bin/env bash` shebang
- Follow shellcheck recommendations
- Use `set -euo pipefail` for safety
- Add function documentation

### Markdown

- Follow markdownlint rules
- Use reference-style links
- Add line breaks after headings
- Keep lines under 120 characters when possible

## Contributing

For contribution guidelines and code of conduct, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Support

- **Issues**: [GitHub Issues](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/discussions)
- **Project Constitution**: `.specify/memory/constitution.md`

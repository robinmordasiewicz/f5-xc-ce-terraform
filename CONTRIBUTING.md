# Contributing to f5-xc-ce-terraform

Thank you for your interest in contributing to the F5 XC Customer Edge Azure deployment project! This document provides guidelines and instructions for contributing.

## Getting Started

Before contributing, please:

1. Read the [Developer Guide](docs/development.md) for complete development environment setup
2. Review the [Project Constitution](.specify/memory/constitution.md) for workflow requirements
3. Familiarize yourself with the [Architecture](docs/architecture.md)

## Development Environment

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/robinmordasiewicz/f5-xc-ce-terraform.git
cd f5-xc-ce-terraform

# Set up development environment (REQUIRED)
./scripts/setup-dev-environment.sh
```

This installs pre-commit hooks, linters, formatters, and other development tools.

**IMPORTANT**: Pre-commit hooks are mandatory. See the [Developer Guide](docs/development.md#pre-commit-hooks-mandatory) for details.

## Contribution Workflow

### 1. Create an Issue

**All work must start with a GitHub issue** - this is a non-negotiable project requirement.

```bash
# Create issue via GitHub CLI
gh issue create --title "Your feature or bug description"

# Or create via web interface
```

### 2. Create Feature Branch

```bash
# Branch naming: [issue-number]-brief-description
git checkout -b 36-add-logging-feature
```

### 3. Verify Issue Context

```bash
# Verify you're on correct branch with valid issue
./.specify/scripts/bash/verify-issue-context.sh
```

This script validates:
- Current branch name matches issue number
- Issue exists and is open
- Branch is not main/master

### 4. Make Changes

- Follow code style guidelines in [Developer Guide](docs/development.md)
- Write clear, descriptive commit messages
- Keep commits focused and atomic
- Add tests for new functionality

### 5. Local Validation

Pre-commit hooks run automatically, but you can also run manually:

```bash
# Run all pre-commit checks
pre-commit run --all-files

# Run specific validations
terraform fmt -check -recursive
terraform validate
tflint
checkov -d terraform/
```

### 6. Commit Changes

```bash
git add <files>
git commit -m "feat: add logging to CE deployment"
# Pre-commit hooks run automatically
```

**Commit Message Format**:
```
<type>: <description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 7. Push and Create Pull Request

```bash
git push origin [branch-name]

# Create PR via GitHub CLI
gh pr create --title "Add logging feature" --body "Closes #36"
```

## Pull Request Guidelines

### PR Requirements

- ✅ Linked to GitHub issue (e.g., "Closes #36")
- ✅ Clear description of changes and reasoning
- ✅ All CI/CD checks passing
- ✅ Pre-commit hooks passing
- ✅ Tests added/updated for changes
- ✅ Documentation updated if needed

### PR Template

```markdown
## Description
Brief description of changes

## Related Issue
Closes #[issue-number]

## Changes Made
- Change 1
- Change 2

## Testing
- How changes were tested
- Test results

## Documentation
- Documentation added/updated

## Checklist
- [ ] Pre-commit hooks passing
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Ready for review
```

## Code Quality Standards

### Terraform

- Use `terraform fmt` for formatting
- Follow [HashiCorp Style Guide](https://www.terraform.io/docs/language/syntax/style.html)
- Document modules with README.md
- Use meaningful resource names
- Add comments for complex logic

### YAML

- 2-space indentation
- Follow `.yamllint` configuration
- No trailing whitespace
- Use `true`/`false` not `yes`/`no`

### Shell Scripts

- Use `#!/usr/bin/env bash` shebang
- Follow shellcheck recommendations
- Use `set -euo pipefail`
- Document functions with comments

### Markdown

- Follow markdownlint rules
- Use reference-style links for readability
- Add blank line after headings
- Keep line length reasonable (<120 chars when practical)

## Testing Requirements

### Required Tests

- **Unit Tests**: For new functions/modules
- **Integration Tests**: For infrastructure changes
- **Security Scans**: Automated via pre-commit
- **Validation**: Terraform validate must pass

### Running Tests

See [Developer Guide - Local Testing](docs/development.md#local-testing) for detailed instructions.

## Documentation Requirements

When contributing, update documentation as needed:

- **README.md**: Only for user-facing deployment changes
- **docs/architecture.md**: For architectural changes
- **docs/development.md**: For development workflow changes
- **docs/requirements.md**: For prerequisite changes
- **Module README**: For module-specific changes

## Issue and Bug Reports

### Creating Issues

Use descriptive titles and provide:

- Clear description of issue/feature
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (Azure region, Terraform version, etc.)
- Relevant logs or error messages

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Documentation improvements
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention needed

## Communication

### Channels

- **Issues**: Bug reports, feature requests
- **Pull Requests**: Code review and discussion
- **Discussions**: General questions and ideas

### Response Times

- Issues: Acknowledged within 48 hours
- Pull Requests: Initial review within 3 business days
- Security Issues: Responded to within 24 hours

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Prioritize community well-being

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

### Enforcement

Project maintainers will remove, edit, or reject comments, commits, and contributions that violate these standards.

## Security

### Reporting Security Issues

**DO NOT** create public issues for security vulnerabilities.

Instead:
1. Email security contact (see SECURITY.md)
2. Provide detailed description
3. Include steps to reproduce
4. Wait for response before disclosure

### Security Best Practices

- Never commit secrets or credentials
- Use workload identity federation
- Store sensitive data in Azure Key Vault
- Run security scans before committing
- Follow least privilege principle

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Additional Resources

- **[Developer Guide](docs/development.md)** - Complete development documentation
- **[Architecture](docs/architecture.md)** - Technical architecture details
- **[Requirements](docs/requirements.md)** - System requirements
- **[Project Constitution](.specify/memory/constitution.md)** - Workflow standards
- **[F5 XC Documentation](https://docs.cloud.f5.com)** - F5 XC official docs
- **[Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)** - Terraform guidelines

## Questions?

If you have questions:

1. Check existing documentation
2. Search closed issues
3. Open a new discussion
4. Contact maintainers

Thank you for contributing! 🎉

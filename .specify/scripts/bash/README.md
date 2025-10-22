# Workflow Enforcement Scripts

This directory contains scripts that enforce the project's constitution and workflow standards.

## Scripts Overview

### 🔍 verify-issue-context.sh

**Purpose**: Validates that current git context has an associated GitHub issue

**Constitution Reference**: Lines 309-318 (Pre-Action Verification)

**Usage**:
```bash
./.specify/scripts/bash/verify-issue-context.sh
```

**Exit Codes**:
- `0`: Success - valid issue context
- `1`: Not on a feature branch
- `2`: Invalid branch name pattern
- `3`: Branch number doesn't match an open GitHub issue
- `4`: GitHub CLI not available

**When to Run**:
- Before ANY code modification
- At session start for AI agents
- Before creating commits

---

### 🎉 post-merge-cleanup.sh

**Purpose**: Remind and assist with branch cleanup after PR merge

**Constitution Reference**: Lines 104-109, 416-422 (Issue Closure and Branch Cleanup)

**Usage**:
```bash
./.specify/scripts/bash/post-merge-cleanup.sh
```

**Features**:
- Detects current branch and merged status
- Lists local branches that need cleanup
- Provides constitution-compliant cleanup commands
- Offers automatic cleanup execution
- Verifies cleanup completion

**Interactive Mode**:
The script will prompt you to automatically run cleanup steps if you're still on a feature branch.

**Non-Interactive Use**:
Run after merge to verify no stale branches remain:
```bash
git checkout main
./.specify/scripts/bash/post-merge-cleanup.sh
```

---

### 📋 create-new-feature.sh

**Purpose**: Creates a new feature with proper issue and branch setup

**Constitution Reference**: Lines 33-80 (STEP ZERO: Issue Creation)

**Usage**:
```bash
./.specify/scripts/bash/create-new-feature.sh
```

**Workflow**:
1. Creates GitHub issue
2. Creates feature branch with issue number
3. Runs verification checks
4. Ready for implementation

---

### ⚙️ Common Usage Patterns

#### Starting New Work
```bash
# Option 1: Manual workflow (constitution-compliant)
gh issue create --title "Feature description"
git checkout -b [issue-number]-feature-name
./.specify/scripts/bash/verify-issue-context.sh

# Option 2: Automated workflow (recommended)
./.specify/scripts/bash/create-new-feature.sh
```

#### After PR Merge
```bash
# Option 1: Automatic (recommended)
./.specify/scripts/bash/post-merge-cleanup.sh
# Follow prompts for automatic cleanup

# Option 2: Manual cleanup
git checkout main
git pull origin main
git branch -d [branch-name]
git push origin --delete [branch-name]
git branch -a  # Verify cleanup
```

#### AI Agent Session Start
```bash
# Required verification before code changes
git branch --show-current
./.specify/scripts/bash/verify-issue-context.sh
```

---

## Automation Integration

### GitHub Actions

**branch-cleanup.yml**: Automatically deletes merged feature branches

- **Trigger**: PR merge event
- **Actions**:
  - Deletes remote feature branch
  - Posts cleanup reminder comment on PR
  - Creates summary in workflow run
- **Location**: `.github/workflows/branch-cleanup.yml`

### Pre-commit Hooks

Pre-commit hooks enforce code quality but do NOT enforce issue workflow. Issue workflow is enforced by:
- `verify-issue-context.sh` (run manually or by agents)
- GitHub branch protection rules
- Code review process

---

## Constitution Compliance

All scripts enforce the project constitution located at:
`.specify/memory/constitution.md`

Key principles enforced:
1. **Issue-First Workflow**: All work must start with a GitHub issue
2. **Branch Naming**: `[issue-number]-description` pattern required
3. **Branch Cleanup**: Mandatory deletion after merge
4. **Verification**: All checks must pass before work begins

---

## Troubleshooting

### "Not on a feature branch" Error
```bash
# Solution: Create feature branch from issue
git checkout -b [issue-number]-description main
```

### "Invalid branch name" Error
```bash
# Solution: Rename branch or create new one
git checkout -b [issue-number]-description
git branch -D old-branch-name
```

### "Issue not found" Error
```bash
# Solution: Create GitHub issue first
gh issue create --title "Description"
# Then create branch with returned issue number
```

### Stale Branch Detection
```bash
# List merged branches needing cleanup
git branch --merged | grep -v "main\|master"

# Run cleanup script for assistance
./.specify/scripts/bash/post-merge-cleanup.sh
```

---

## Best Practices

### ✅ Do
- Run `verify-issue-context.sh` before starting work
- Run `post-merge-cleanup.sh` after every PR merge
- Use `create-new-feature.sh` for consistent workflow
- Check script exit codes in automation
- Review constitution references for context

### ❌ Don't
- Skip verification checks
- Create branches without GitHub issues
- Leave stale branches after merge
- Work directly on main/master
- Bypass constitution requirements

---

## Script Maintenance

### Adding New Scripts
1. Place in `.specify/scripts/bash/`
2. Make executable: `chmod +x script.sh`
3. Follow naming convention: `kebab-case.sh`
4. Include constitution references in comments
5. Update this README with usage information

### Testing Scripts
```bash
# Test in safe branch
git checkout -b test-scripts
./script.sh
# Verify behavior
git checkout main
git branch -D test-scripts
```

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
**Maintainer**: Project Team

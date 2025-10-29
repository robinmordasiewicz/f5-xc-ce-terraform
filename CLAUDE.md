# f5-xc-ce-terraform Development Guidelines

## 🚨 MANDATORY WORKFLOW - READ BEFORE ANY ACTION

### CRITICAL: Issue-First Discipline (NON-NEGOTIABLE)

**⛔ STOP! Before performing ANY implementation work, verify:**

1. **✅ Does a GitHub issue exist for this work?**
   - If **YES** → Note issue number, proceed to step 2
   - If **NO** → **STOP!** Create issue FIRST: `gh issue create`
   - Never start work without a GitHub issue - **NO EXCEPTIONS**

2. **✅ Am I on the correct feature branch?**
   - Run: `git branch --show-current`
   - Should show: `[issue-number]-description` (e.g., `42-add-logging`)
   - If on `main` or `master` → **STOP!** Create feature branch first
   - Command: `git checkout -b [issue-number]-description`

3. **✅ Run pre-flight verification:**
   - Execute: `./.specify/scripts/bash/verify-issue-context.sh`
   - Must return exit code 0 (success) before proceeding
   - Script validates: branch name, issue exists, issue is open

**❌ PROHIBITED ACTIONS without pre-existing GitHub issue:**
- Edit, Write, or code modification tools
- Creating branches or making commits
- "Quick fixes" or "small changes"
- Any implementation work whatsoever

**✅ ALLOWED ACTIONS without GitHub issue:**
- Reading documentation or constitution
- Creating the GitHub issue itself
- Answering questions about the codebase
- Exploring and understanding existing code

**🔄 IMPLICIT WORK REQUESTS (Automatic Workflow Trigger):**
When a user reports any of the following, **automatically** create issue → branch → fix → test → PR (DO NOT ASK):
- Error reports ("This is broken", "Getting error X")
- Bug descriptions ("When I do X, Y happens instead of Z")
- Test failures ("Tests are failing", "Build is broken")
- Performance issues ("This is slow", "System is timing out")
- Security vulnerabilities ("Found security issue")
- Regression reports ("This used to work but now doesn't")

**⚠️ CONFIRMATION REQUIRED before proceeding:**
- Major architectural changes affecting multiple systems
- Breaking changes that affect public APIs or workflows
- Destructive operations (data deletion, resource removal)
- Changes requiring >4 hours estimated effort
- Ambiguous requirements with multiple valid solutions

**📖 Full Constitution**: See `.specify/memory/constitution.md` for complete workflow rules, quality standards, and testing requirements.

---

Auto-generated from all feature plans. Last updated: 2025-10-21

## Active Technologies
- HCL (Terraform 1.6+) (001-ce-cicd-automation)

## Project Structure
```
src/
tests/
```

## Commands
# Add commands for HCL (Terraform 1.6+)

## Code Style
HCL (Terraform 1.6+): Follow standard conventions

## Recent Changes
- 001-ce-cicd-automation: Added HCL (Terraform 1.6+)

<!-- MANUAL ADDITIONS START -->

## GitHub Label Management Protocol

**CRITICAL**: Always check and create labels BEFORE using them in issue creation.

### Correct Workflow:
1. **Check existing labels first**: `gh label list`
2. **Create missing labels**: `gh label create "label-name" --description "..." --color "hexcode"`
3. **Then create issue** with labels: `gh issue create ... --label "label-name"`

### Available Labels:
- `bug` - Something isn't working (#d73a4a)
- `enhancement` - New feature or request (#a2eeef)
- `documentation` - Improvements or additions to documentation (#0075ca)
- `github-actions` - GitHub Actions workflows and CI/CD (#0366d6)
- `azure` - Azure cloud infrastructure and services (#0078d4)
- `terraform` - Terraform infrastructure as code (#5c4ee5)
- `backend-configuration` - Backend state storage configuration (#d4c5f9)
- `diagram-quality` - Diagram generation quality and visual standards (#1d76db)
- `visual-design` - Visual design and user interface improvements (#d4c5f9)
- `high-priority` - High priority items requiring immediate attention (#d93f0b)
- `code-quality` - Code quality, linting, and style issues (#fbca04)

### Label Creation Examples:
```bash
# Check existing labels first
gh label list

# Create missing label before using it
gh label create "code-quality" --description "Code quality, linting, and style issues" --color "fbca04"

# Now create issue with the label
gh issue create --title "..." --body "..." --label "code-quality"
```

### Common Mistakes to Avoid:
❌ **WRONG**: `gh issue create ... --label "new-label"` → Error: label not found
✅ **RIGHT**: `gh label list` → `gh label create "new-label" ...` → `gh issue create ... --label "new-label"`

<!-- MANUAL ADDITIONS END -->

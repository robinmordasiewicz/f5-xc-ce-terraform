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
<!-- MANUAL ADDITIONS END -->

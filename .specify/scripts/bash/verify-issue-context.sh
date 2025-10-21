#!/bin/bash
#
# Verify Issue Context - Constitution Enforcement Script
#
# This script verifies that the current git context has an associated GitHub issue.
# It enforces the constitution's Issue-First Discipline (Section I).
#
# Purpose:
# - Prevent work on main/master branches
# - Ensure feature branches follow naming convention: [issue-number]-description
# - Verify GitHub issue exists and is accessible
# - Warn if working on closed issues
#
# Return Codes:
# - 0: Success - valid issue context
# - 1: Error - working on main/master branch
# - 2: Error - invalid branch name (no issue number)
# - 3: Error - GitHub issue doesn't exist
# - 4: Warning - GitHub issue is closed (allows continuation)
#
# Usage:
#   ./verify-issue-context.sh
#   echo $?  # Check return code
#

set -e # Exit on error for commands, but we'll handle specific cases

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
}

# Get current branch name
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

if [ -z "$CURRENT_BRANCH" ]; then
  print_error "Not in a git repository or detached HEAD state"
  exit 1
fi

print_info "Current branch: $CURRENT_BRANCH"

# Check if on main or master branch
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  print_error "CONSTITUTION VIOLATION: Cannot work on '$CURRENT_BRANCH' branch"
  echo ""
  echo "Required workflow:"
  echo "  1. Create GitHub issue first: gh issue create"
  echo "  2. Create feature branch: git checkout -b [issue-number]-description"
  echo "  3. Then proceed with work"
  echo ""
  exit 1
fi

# Extract issue number from branch name (pattern: [0-9]+-description)
ISSUE_NUMBER=$(echo "$CURRENT_BRANCH" | grep -oE '^[0-9]+' || echo "")

if [ -z "$ISSUE_NUMBER" ]; then
  print_error "CONSTITUTION VIOLATION: Branch name must start with issue number"
  echo ""
  echo "Current branch: $CURRENT_BRANCH"
  echo "Required pattern: [issue-number]-description"
  echo "Example: 42-add-logging"
  echo ""
  echo "Fix:"
  echo "  1. Find or create GitHub issue"
  echo "  2. Rename branch: git branch -m $CURRENT_BRANCH [issue-number]-description"
  echo "  OR"
  echo "  3. Create new branch: git checkout -b [issue-number]-description"
  echo ""
  exit 2
fi

print_info "Detected issue number: #$ISSUE_NUMBER"

# Check if gh CLI is available
if ! command -v gh &>/dev/null; then
  print_warning "GitHub CLI (gh) not found - cannot verify issue exists"
  print_warning "Install from: https://cli.github.com/"
  print_success "Branch naming is correct (#$ISSUE_NUMBER), proceeding with trust"
  exit 0
fi

# Verify issue exists in GitHub
print_info "Verifying issue #$ISSUE_NUMBER exists in GitHub..."

# Attempt to get issue information
ISSUE_INFO=$(gh issue view "$ISSUE_NUMBER" --json title,state,url 2>/dev/null || echo "")

if [ -z "$ISSUE_INFO" ]; then
  print_error "CONSTITUTION VIOLATION: Issue #$ISSUE_NUMBER does not exist in GitHub"
  echo ""
  echo "Branch: $CURRENT_BRANCH"
  echo "Expected issue: #$ISSUE_NUMBER"
  echo ""
  echo "Fix:"
  echo "  1. Create the issue: gh issue create"
  echo "  2. Update branch name to match issue number"
  echo "  OR"
  echo "  3. Check if you meant a different issue number"
  echo ""
  exit 3
fi

# Parse issue information
# Use jq if available, otherwise fall back to basic parsing
if command -v jq &>/dev/null; then
  ISSUE_TITLE=$(echo "$ISSUE_INFO" | jq -r '.title // "Unknown"')
  ISSUE_STATE=$(echo "$ISSUE_INFO" | jq -r '.state // "Unknown"')
  ISSUE_URL=$(echo "$ISSUE_INFO" | jq -r '.url // ""')
else
  # Fallback parsing without jq (less robust but works)
  ISSUE_TITLE=$(echo "$ISSUE_INFO" | sed -n 's/.*"title":"\([^"]*\)".*/\1/p')
  ISSUE_STATE=$(echo "$ISSUE_INFO" | sed -n 's/.*"state":"\([^"]*\)".*/\1/p')
  ISSUE_URL=$(echo "$ISSUE_INFO" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')

  # If parsing failed, use defaults
  [ -z "$ISSUE_TITLE" ] && ISSUE_TITLE="Unknown"
  [ -z "$ISSUE_STATE" ] && ISSUE_STATE="Unknown"
fi

print_success "Issue #$ISSUE_NUMBER found: $ISSUE_TITLE"

# Check if issue is closed
if [ "$ISSUE_STATE" = "CLOSED" ]; then
  print_warning "Issue #$ISSUE_NUMBER is CLOSED"
  print_warning "Verify you should be working on a closed issue"
  echo ""
  echo "Title: $ISSUE_TITLE"
  echo "URL: $ISSUE_URL"
  echo ""
  echo "If this is incorrect:"
  echo "  - Reopen issue: gh issue reopen $ISSUE_NUMBER"
  echo "  - Create new issue and update branch name"
  echo ""
  # Return warning code but allow continuation
  exit 4
fi

# All checks passed
echo ""
print_success "✨ Issue context validated successfully!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Working on Issue #$ISSUE_NUMBER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Branch: $CURRENT_BRANCH"
echo "Title: $ISSUE_TITLE"
echo "State: $ISSUE_STATE"
echo "URL: $ISSUE_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit 0

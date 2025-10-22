#!/usr/bin/env bash
#
# Post-Merge Cleanup Reminder Script
#
# Purpose: Remind developers to clean up branches after PR merge
# Constitution Reference: Lines 104-109, 416-422
#
# Usage: Run this script after merging a PR to ensure constitution compliance
#

set -euo pipefail

# ANSI color codes
readonly BLUE='\033[0;34m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m' # No Color

# Icons
readonly INFO="ℹ️ "
readonly SUCCESS="✅"
readonly WARNING="⚠️ "
readonly ERROR="❌"

# Function to print colored messages
print_info() { echo -e "${BLUE}${INFO}${1}${NC}"; }
print_success() { echo -e "${GREEN}${SUCCESS} ${1}${NC}"; }
print_warning() { echo -e "${YELLOW}${WARNING}${1}${NC}"; }
print_error() { echo -e "${RED}${ERROR} ${1}${NC}"; }

# Function to print section headers
print_header() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main() {
  print_header "🎉 PR Merged Successfully!"

  local current_branch
  current_branch=$(git branch --show-current)

  # Check if we're on main/master
  if [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
    print_success "You're on the main branch - good!"
    print_info "Checking for stale local branches that might need cleanup..."

    # Find merged branches (excluding main/master)
    local merged_branches
    merged_branches=$(git branch --merged | grep -v "^\*" | grep -v "main" | grep -v "master" | xargs || true)

    if [[ -n "$merged_branches" ]]; then
      print_warning "Found merged local branches that may need cleanup:"
      while IFS= read -r branch; do
        echo "    - $branch"
      done <<<"$merged_branches"
      echo ""
      print_info "To delete these branches, run:"
      for branch in $merged_branches; do
        echo "    git branch -d $branch"
      done
    else
      print_success "No stale merged branches found locally"
    fi

    # Check for remote branches that might be stale
    print_info "Checking for stale remote branches..."
    git fetch --prune origin >/dev/null 2>&1 || true

    print_success "Branch cleanup check complete!"

  else
    print_warning "You're still on feature branch: $current_branch"
    echo ""
    print_header "📋 Constitution-Required Cleanup Steps"
    echo ""
    echo "After PR merge, you MUST complete these steps:"
    echo ""
    echo "1. Switch to main branch:"
    echo "   ${GREEN}git checkout main${NC}"
    echo ""
    echo "2. Update main branch:"
    echo "   ${GREEN}git pull origin main${NC}"
    echo ""
    echo "3. Delete local feature branch:"
    echo "   ${GREEN}git branch -d $current_branch${NC}"
    echo ""
    echo "4. Delete remote feature branch:"
    echo "   ${GREEN}git push origin --delete $current_branch${NC}"
    echo ""
    echo "5. Verify cleanup:"
    echo "   ${GREEN}git branch -a${NC}"
    echo ""
    print_info "Constitution Reference: Section I.IV - Issue Closure and Branch Cleanup"
    print_info "Location: .specify/memory/constitution.md lines 104-109, 416-422"
    echo ""

    # Offer to run cleanup automatically
    echo ""
    read -p "Would you like to run the cleanup steps automatically? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      print_info "Running automatic cleanup..."

      # Switch to main
      print_info "Switching to main branch..."
      git checkout main

      # Update main
      print_info "Updating main branch..."
      git pull origin main

      # Delete local branch
      print_info "Deleting local branch: $current_branch"
      git branch -d "$current_branch"

      # Delete remote branch
      print_info "Deleting remote branch: $current_branch"
      git push origin --delete "$current_branch" || print_warning "Remote branch may already be deleted"

      # Verify
      print_success "Cleanup complete! Verifying..."
      if git branch -a | grep -q "$current_branch"; then
        print_error "Branch still exists!"
      else
        print_success "Branch successfully removed"
      fi

      print_success "✨ All cleanup steps completed!"
    else
      print_warning "Please run the cleanup steps manually"
      print_info "Re-run this script after cleanup to verify"
    fi
  fi

  print_header "Branch Cleanup Summary"
  echo "Current branch: $(git branch --show-current)"
  echo "Local branches: $(git branch | wc -l | xargs)"
  echo "Remote branches: $(git branch -r | wc -l | xargs)"
  echo ""
}

# Run main function
main "$@"

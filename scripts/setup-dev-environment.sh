#!/bin/bash
#
# Developer Environment Setup Script
#
# Sets up local development environment with required tools and pre-commit hooks
#
# Prerequisites:
# - Git
# - Python 3.11+
# - pip
#
# Usage:
#   ./scripts/setup-dev-environment.sh
#

set -e # Exit on error

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

print_header() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
}

# Main setup function
main() {
  print_header "F5 XC CE Terraform - Developer Environment Setup"

  # Check if we're in the repository root
  if [ ! -f ".pre-commit-config.yaml" ]; then
    print_error "Not in repository root. Please run from: cd \$(git rev-parse --show-toplevel)"
    exit 1
  fi

  print_info "This script will install and configure:"
  echo "  • Pre-commit framework and hooks"
  echo "  • Code quality tools (linters, formatters)"
  echo "  • Security scanning tools"
  echo "  • Git hooks for constitution compliance"
  echo ""

  # Step 1: Check Python installation
  print_info "Step 1/6: Checking Python installation..."

  if ! command -v python3 &>/dev/null; then
    print_error "Python 3 not found. Please install Python 3.11 or later"
    exit 1
  fi

  PYTHON_VERSION=$(python3 --version | awk '{print $2}')
  print_success "Python $PYTHON_VERSION found"

  # Step 2: Check pip installation
  print_info "Step 2/6: Checking pip installation..."

  if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
    print_error "pip not found. Please install pip"
    exit 1
  fi

  PIP_CMD="pip3"
  if ! command -v pip3 &>/dev/null; then
    PIP_CMD="pip"
  fi

  print_success "pip found"

  # Step 3: Install pre-commit framework
  print_info "Step 3/6: Installing pre-commit framework..."

  if $PIP_CMD show pre-commit &>/dev/null; then
    PRECOMMIT_VERSION=$($PIP_CMD show pre-commit | grep Version | awk '{print $2}')
    print_warning "pre-commit already installed (version $PRECOMMIT_VERSION)"
  else
    $PIP_CMD install pre-commit
    print_success "pre-commit framework installed"
  fi

  # Step 4: Install detect-secrets
  print_info "Step 4/6: Installing detect-secrets..."

  if $PIP_CMD show detect-secrets &>/dev/null; then
    DETECT_SECRETS_VERSION=$($PIP_CMD show detect-secrets | grep Version | awk '{print $2}')
    print_warning "detect-secrets already installed (version $DETECT_SECRETS_VERSION)"
  else
    $PIP_CMD install detect-secrets
    print_success "detect-secrets installed"
  fi

  # Step 5: Install pre-commit hooks
  print_info "Step 5/6: Installing pre-commit hooks..."

  # Check if hooks are already installed
  if [ -f ".git/hooks/pre-commit" ]; then
    if grep -q "pre-commit.com" ".git/hooks/pre-commit" 2>/dev/null; then
      print_warning "Pre-commit hooks already installed"
    else
      print_info "Migrating existing hooks to pre-commit framework..."
      pre-commit install
      print_success "Pre-commit hooks installed (existing hooks backed up)"
    fi
  else
    pre-commit install
    print_success "Pre-commit hooks installed"
  fi

  # Step 6: Install hook dependencies
  print_info "Step 6/6: Installing pre-commit hook dependencies..."
  print_info "This may take a few minutes on first run..."

  if pre-commit install-hooks; then
    print_success "Pre-commit hook dependencies installed"
  else
    print_warning "Some hook dependencies may need manual installation"
    print_info "Run 'pre-commit run --all-files' to see which tools are needed"
  fi

  # Success summary
  print_header "✨ Developer Environment Setup Complete!"

  echo "Pre-commit hooks are now active and will run automatically on:"
  echo "  • Every git commit"
  echo "  • All file types in the repository"
  echo ""
  echo "Important Constitution Requirements:"
  echo "  ⚠️  Pre-commit hooks are READ-ONLY (no auto-fix)"
  echo "  ⚠️  You MUST manually fix all reported errors"
  echo "  ⚠️  Bypassing hooks is STRICTLY FORBIDDEN"
  echo "  ⚠️  git commit --no-verify is PROHIBITED"
  echo ""
  echo "Validation Coverage:"
  echo "  ✅ Terraform: fmt check, validate, docs, tflint, checkov"
  echo "  ✅ YAML: yamllint, syntax validation"
  echo "  ✅ JSON: syntax validation, formatting check"
  echo "  ✅ Markdown: markdownlint, formatting check"
  echo "  ✅ Shell: shellcheck, shfmt check"
  echo "  ✅ Python: ruff, black check, mypy"
  echo "  ✅ Go: gofmt check, golangci-lint"
  echo "  ✅ Security: detect-secrets, checkov"
  echo "  ✅ General: trailing whitespace, line endings, merge conflicts"
  echo ""
  echo "Testing Pre-commit Hooks:"
  echo "  Run on all files:   pre-commit run --all-files"
  echo "  Run specific hook:  pre-commit run <hook-id>"
  echo "  Update hooks:       pre-commit autoupdate"
  echo ""
  echo "If a commit is blocked:"
  echo "  1. Read the error message carefully"
  echo "  2. Fix the reported issues manually"
  echo "  3. Stage the fixes: git add <files>"
  echo "  4. Commit again: git commit"
  echo ""
  echo "Need help? See README.md section: Pre-commit Hooks"
  echo ""
  print_success "Ready to start development! 🚀"
  echo ""
}

# Run main function
main

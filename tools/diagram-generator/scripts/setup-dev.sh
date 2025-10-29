#!/usr/bin/env bash
#
# Development environment setup script
# Usage: ./scripts/setup-dev.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${BLUE}=== Azure + F5 XC Diagram Generator - Development Setup ===${NC}\n"

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
REQUIRED_VERSION="3.9"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
  echo -e "${RED}✗ Python 3.9 or higher required. Found: $PYTHON_VERSION${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}\n"

# Check if virtual environment exists
echo -e "${YELLOW}Setting up virtual environment...${NC}"
cd "$PROJECT_DIR"

if [ ! -d "venv" ]; then
  echo "Creating new virtual environment..."
  python3 -m venv venv
  echo -e "${GREEN}✓ Virtual environment created${NC}"
else
  echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip upgraded${NC}"

# Install package in development mode
echo -e "\n${YELLOW}Installing package with development dependencies...${NC}"
pip install -e ".[dev]" --quiet
echo -e "${GREEN}✓ Package installed${NC}"

# Install pre-commit hooks
echo -e "\n${YELLOW}Installing pre-commit hooks...${NC}"
pre-commit install
echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"

# Check required tools
echo -e "\n${YELLOW}Checking optional tools...${NC}"

# Check Terraform
if command -v terraform &>/dev/null; then
  TERRAFORM_VERSION=$(terraform version | head -n1 | cut -d'v' -f2)
  echo -e "${GREEN}✓ Terraform $TERRAFORM_VERSION${NC}"
else
  echo -e "${YELLOW}⚠ Terraform not found (optional for testing)${NC}"
fi

# Check Azure CLI
if command -v az &>/dev/null; then
  AZ_VERSION=$(az version --output tsv 2>/dev/null | grep "azure-cli" | awk '{print $2}')
  echo -e "${GREEN}✓ Azure CLI $AZ_VERSION${NC}"
else
  echo -e "${YELLOW}⚠ Azure CLI not found (required for Azure authentication)${NC}"
fi

# Check OpenSSL
if command -v openssl &>/dev/null; then
  OPENSSL_VERSION=$(openssl version | cut -d' ' -f2)
  echo -e "${GREEN}✓ OpenSSL $OPENSSL_VERSION${NC}"
else
  echo -e "${YELLOW}⚠ OpenSSL not found (required for P12 certificate extraction)${NC}"
fi

# Run tests to verify installation
echo -e "\n${YELLOW}Running tests to verify installation...${NC}"
if pytest tests/ -q --tb=no; then
  echo -e "${GREEN}✓ All tests passed${NC}"
else
  echo -e "${RED}✗ Some tests failed${NC}"
fi

# Create example .env file if it doesn't exist
echo -e "\n${YELLOW}Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
  cat >.env <<'EOF'
# Azure Configuration
export AZURE_SUBSCRIPTION_ID="your-subscription-id"

# F5 XC Configuration
export F5XC_TENANT="your-tenant-name"
export F5XC_API_TOKEN="your-api-token"

# Lucidchart Configuration
export LUCID_CLIENT_ID="your-lucid-client-id"
export LUCID_CLIENT_SECRET="your-lucid-client-secret"
export LUCID_REDIRECT_URI="http://localhost:8080/callback"
EOF
  echo -e "${GREEN}✓ Created .env template${NC}"
  echo -e "${YELLOW}  → Edit .env with your credentials${NC}"
else
  echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Summary
echo -e "\n${BLUE}=== Setup Complete! ===${NC}\n"
echo -e "Next steps:"
echo -e "  1. Activate virtual environment: ${GREEN}source venv/bin/activate${NC}"
echo -e "  2. Configure credentials: ${GREEN}edit .env${NC}"
echo -e "  3. Run tests: ${GREEN}pytest${NC}"
echo -e "  4. Generate diagram: ${GREEN}generate-diagram --help${NC}"
echo -e "\nDevelopment commands:"
echo -e "  ${GREEN}pytest${NC}                  Run tests"
echo -e "  ${GREEN}pytest --cov${NC}            Run tests with coverage"
echo -e "  ${GREEN}black src/ tests/${NC}       Format code"
echo -e "  ${GREEN}ruff check src/${NC}         Lint code"
echo -e "  ${GREEN}mypy src/${NC}               Type check"
echo -e "  ${GREEN}pre-commit run --all${NC}    Run all pre-commit hooks"
echo -e "\nDocumentation:"
echo -e "  ${BLUE}README.md${NC}               User guide"
echo -e "  ${BLUE}CONTRIBUTING.md${NC}         Development guide"
echo -e "  ${BLUE}example-config.yaml${NC}     Configuration example"
echo ""

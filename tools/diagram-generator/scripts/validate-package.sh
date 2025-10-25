#!/usr/bin/env bash
#
# Package validation script
# Runs all quality checks without installing dependencies
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Package Validation ==="
echo ""

cd "$PROJECT_DIR"

# Check Python syntax
echo -n "Checking Python syntax... "
if python3 -m py_compile src/diagram_generator/*.py 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Check Python syntax for tests
echo -n "Checking test syntax... "
if python3 -m py_compile tests/*.py 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Check pyproject.toml
echo -n "Validating pyproject.toml... "
if python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" 2>/dev/null || python3 -c "import tomli; tomli.load(open('pyproject.toml', 'rb'))" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Check required files exist
echo -n "Checking required files... "
REQUIRED_FILES=(
    "README.md"
    "LICENSE"
    "CONTRIBUTING.md"
    "CHANGELOG.md"
    "pyproject.toml"
    ".pre-commit-config.yaml"
    "example-config.yaml"
    "src/diagram_generator/__init__.py"
    "src/diagram_generator/cli.py"
    "src/diagram_generator/models.py"
    "tests/__init__.py"
    "tests/conftest.py"
)

MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC}"
        echo "  Missing: $file"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -eq 0 ]; then
    echo -e "${GREEN}✓${NC}"
else
    exit 1
fi

# Check directory structure
echo -n "Checking directory structure... "
REQUIRED_DIRS=(
    "src/diagram_generator"
    "tests"
    "scripts"
    ".github/workflows"
)

MISSING_DIRS=0
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "${RED}✗${NC}"
        echo "  Missing directory: $dir"
        MISSING_DIRS=$((MISSING_DIRS + 1))
    fi
done

if [ $MISSING_DIRS -eq 0 ]; then
    echo -e "${GREEN}✓${NC}"
else
    exit 1
fi

# Check for __pycache__ pollution
echo -n "Checking for __pycache__ pollution... "
if find . -type d -name "__pycache__" | grep -q .; then
    echo -e "${YELLOW}⚠${NC}"
    echo "  Run: find . -type d -name '__pycache__' -exec rm -rf {} +"
else
    echo -e "${GREEN}✓${NC}"
fi

# Check line counts
echo ""
echo "Code statistics:"
echo -n "  Source files: "
find src/ -name "*.py" | wc -l | tr -d ' '
echo -n "  Test files: "
find tests/ -name "*.py" | wc -l | tr -d ' '
echo -n "  Total lines of code: "
find src/ -name "*.py" -exec cat {} \; | wc -l | tr -d ' '
echo -n "  Total lines of tests: "
find tests/ -name "*.py" -exec cat {} \; | wc -l | tr -d ' '

echo ""
echo -e "${GREEN}=== All validation checks passed! ===${NC}"

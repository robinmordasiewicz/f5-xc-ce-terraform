#!/usr/bin/env bash
# Naming Convention Validation Test
# Tests Azure resource names against Azure CAF standards and project requirements
#
# Usage: ./tests/validate-naming-conventions.sh [--mode=current|target]
#
# Modes:
#   current - Validate current naming (baseline test)
#   target  - Validate target naming (goal state)
#
# Exit codes:
#   0 - All tests passed
#   1 - Tests failed
#   2 - Missing dependencies or configuration

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test mode (current or target)
MODE="${1:-current}"
if [[ "$MODE" == "--mode=current" ]] || [[ "$MODE" == "--mode=target" ]]; then
  MODE="${MODE#--mode=}"
fi

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Test results array
declare -a FAILED_TESTS=()

# Helper functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
  echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
  echo -e "${RED}[✗]${NC} $*"
}

log_warn() {
  echo -e "${YELLOW}[⚠]${NC} $*"
}

test_pass() {
  ((TESTS_PASSED++))
  ((TESTS_TOTAL++))
  log_success "$1"
}

test_fail() {
  ((TESTS_FAILED++))
  ((TESTS_TOTAL++))
  FAILED_TESTS+=("$1")
  log_error "$1"
}

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."

  if ! command -v terraform &>/dev/null; then
    log_error "terraform not found. Please install Terraform."
    exit 2
  fi

  if ! command -v az &>/dev/null; then
    log_error "Azure CLI not found. Please install Azure CLI."
    exit 2
  fi

  if [ ! -f "terraform/environments/dev/main.tf" ]; then
    log_error "Not in project root directory. Please run from project root."
    exit 2
  fi

  log_success "Prerequisites check passed"
}

# Get Terraform outputs
get_terraform_outputs() {
  log_info "Retrieving Terraform state..."

  cd terraform/environments/dev || exit 2

  # Check if state exists
  if ! terraform state list &>/dev/null; then
    log_warn "No Terraform state found. Skipping runtime validation."
    return 1
  fi

  # Export outputs as variables
  export TF_HUB_VNET_NAME=$(terraform output -raw hub_vnet_name 2>/dev/null || echo "")
  export TF_LB_NAME=$(terraform output -json deployment_summary 2>/dev/null | jq -r '.load_balancer' 2>/dev/null || echo "")
  export TF_CE_VM_1=$(terraform output -raw ce_vm_1_name 2>/dev/null || echo "")
  export TF_CE_VM_2=$(terraform output -raw ce_vm_2_name 2>/dev/null || echo "")
  export TF_SITE_NAME=$(terraform output -raw ce_site_name 2>/dev/null || echo "")

  cd - >/dev/null

  log_success "Terraform outputs retrieved"
  return 0
}

# Azure CAF naming validation functions
validate_vnet_name() {
  local name=$1
  local expected_pattern=$2
  local description=$3

  ((TESTS_TOTAL++))
  if [[ "$name" =~ $expected_pattern ]]; then
    test_pass "$description: '$name' matches pattern '$expected_pattern'"
  else
    test_fail "$description: '$name' does NOT match pattern '$expected_pattern'"
  fi
}

validate_subnet_name() {
  local name=$1
  local expected_pattern=$2
  local description=$3

  ((TESTS_TOTAL++))
  if [[ "$name" =~ $expected_pattern ]]; then
    test_pass "$description: '$name' matches pattern '$expected_pattern'"
  else
    test_fail "$description: '$name' does NOT match pattern '$expected_pattern'"
  fi
}

validate_vm_name() {
  local name=$1
  local expected_pattern=$2
  local description=$3

  ((TESTS_TOTAL++))
  if [[ "$name" =~ $expected_pattern ]]; then
    test_pass "$description: '$name' matches pattern '$expected_pattern'"
  else
    test_fail "$description: '$name' does NOT match pattern '$expected_pattern'"
  fi
}

validate_lb_name() {
  local name=$1
  local expected_pattern=$2
  local description=$3

  ((TESTS_TOTAL++))
  if [[ "$name" =~ $expected_pattern ]]; then
    test_pass "$description: '$name' matches pattern '$expected_pattern'"
  else
    test_fail "$description: '$name' does NOT match pattern '$expected_pattern'"
  fi
}

validate_f5xc_site_name() {
  local name=$1
  local expected_pattern=$2
  local description=$3

  ((TESTS_TOTAL++))
  if [[ "$name" =~ $expected_pattern ]]; then
    test_pass "$description: '$name' matches pattern '$expected_pattern'"
  else
    test_fail "$description: '$name' does NOT match pattern '$expected_pattern'"
  fi
}

# Test current naming conventions
test_current_naming() {
  log_info "Testing CURRENT naming conventions (baseline)..."
  echo ""

  # Hub VNet - currently has F5 XC branding
  validate_vnet_name "$TF_HUB_VNET_NAME" "^xc-ce-hub-vnet$" "Hub VNet (current)"

  # VMs - currently have redundant prefix
  validate_vm_name "$TF_CE_VM_1" "^xc-ce-ce-0[12]$" "CE VM 1 (current)"
  validate_vm_name "$TF_CE_VM_2" "^xc-ce-ce-0[12]$" "CE VM 2 (current)"

  # Load Balancer - currently has redundant prefix
  validate_lb_name "$TF_LB_NAME" "^xc-ce-ce-lb$" "Load Balancer (current)"

  # F5 XC Site - currently has redundant prefix
  validate_f5xc_site_name "$TF_SITE_NAME" "^xc-ce-ce-site$" "F5 XC Site (current)"

  echo ""
}

# Test target naming conventions (Azure CAF compliant)
test_target_naming() {
  log_info "Testing TARGET naming conventions (Azure CAF compliant)..."
  echo ""

  # Hub VNet - should be generic (no F5 XC branding)
  validate_vnet_name "$TF_HUB_VNET_NAME" "^hub-vnet$" "Hub VNet (target: generic, reusable)"

  # VMs - should have clear f5-xc-ce prefix
  validate_vm_name "$TF_CE_VM_1" "^f5-xc-ce-vm-0[12]$" "CE VM 1 (target: f5-xc-ce-vm-01)"
  validate_vm_name "$TF_CE_VM_2" "^f5-xc-ce-vm-0[12]$" "CE VM 2 (target: f5-xc-ce-vm-02)"

  # Load Balancer - should follow Azure CAF lbi- prefix
  validate_lb_name "$TF_LB_NAME" "^lbi-f5-xc-ce$" "Load Balancer (target: lbi-f5-xc-ce)"

  # F5 XC Site - should include owner identifier (GitHub username)
  validate_f5xc_site_name "$TF_SITE_NAME" "^robinmordasiewicz-f5xc-azure-" "F5 XC Site (target: with owner prefix)"

  echo ""
}

# Test subnet naming from Terraform state
test_subnet_naming() {
  log_info "Testing subnet naming conventions..."
  echo ""

  cd terraform/environments/dev || exit 2

  # Get subnet names from state
  local nva_subnet=$(terraform state show 'module.hub_vnet.azurerm_subnet.nva' 2>/dev/null | grep "name " | head -1 | awk '{print $3}' | tr -d '"' || echo "")
  local mgmt_subnet=$(terraform state show 'module.hub_vnet.azurerm_subnet.mgmt' 2>/dev/null | grep "name " | head -1 | awk '{print $3}' | tr -d '"' || echo "")

  cd - >/dev/null

  if [ "$MODE" == "current" ]; then
    # Current naming
    validate_subnet_name "$nva_subnet" "^nva-subnet$" "NVA Subnet (current)"
    validate_subnet_name "$mgmt_subnet" "^management-subnet$" "Management Subnet (current)"
  else
    # Target naming (Azure CAF)
    validate_subnet_name "$nva_subnet" "^snet-hub-external$" "External Subnet (target: snet-hub-external)"
    validate_subnet_name "$mgmt_subnet" "^snet-hub-management$" "Management Subnet (target: snet-hub-management)"
  fi

  echo ""
}

# Test F5 XC site labels
test_f5xc_labels() {
  log_info "Testing F5 XC site labels..."
  echo ""

  # Note: This requires F5 XC CLI or API access
  # For now, we'll check if labels are defined in Terraform code

  cd terraform/environments/dev || exit 2

  if [ "$MODE" == "current" ]; then
    # Current: minimal labels
    if grep -q '"owner"' main.tf; then
      test_pass "F5 XC site has owner label defined"
    else
      test_fail "F5 XC site missing owner label (current: expected to fail)"
    fi
  else
    # Target: comprehensive labels - check site_labels local variable
    local required_labels=("owner" "github_user" "github_repo" "repo_url")
    for label in "${required_labels[@]}"; do
      if grep -A 10 "site_labels = {" main.tf | grep -q "$label"; then
        test_pass "F5 XC site has $label label defined"
      else
        test_fail "F5 XC site missing $label label (target requirement)"
      fi
    done
  fi

  cd - >/dev/null
  echo ""
}

# Print test summary
print_summary() {
  echo ""
  echo "========================================"
  echo "  Test Summary - Mode: $MODE"
  echo "========================================"
  echo -e "Total Tests:  ${BLUE}$TESTS_TOTAL${NC}"
  echo -e "Passed:       ${GREEN}$TESTS_PASSED${NC}"
  echo -e "Failed:       ${RED}$TESTS_FAILED${NC}"

  if [ "$TESTS_FAILED" -gt 0 ]; then
    echo ""
    echo "Failed Tests:"
    for test in "${FAILED_TESTS[@]}"; do
      echo -e "  ${RED}✗${NC} $test"
    done
  fi

  echo "========================================"

  if [ "$TESTS_FAILED" -gt 0 ]; then
    if [ "$MODE" == "current" ]; then
      log_warn "Current naming validation failed - this is expected before refactoring"
      return 0 # Don't fail on current mode
    else
      log_error "Target naming validation failed - refactoring incomplete"
      return 1
    fi
  else
    log_success "All tests passed!"
    return 0
  fi
}

# Main execution
main() {
  echo "========================================"
  echo "  Naming Convention Validation Test"
  echo "  Mode: $MODE"
  echo "========================================"
  echo ""

  check_prerequisites

  if ! get_terraform_outputs; then
    log_warn "Skipping runtime tests - no Terraform state available"
    log_info "Will validate code-level naming conventions only"
  fi

  # Run appropriate tests based on mode
  if [ "$MODE" == "current" ]; then
    test_current_naming
  elif [ "$MODE" == "target" ]; then
    test_target_naming
  else
    log_error "Invalid mode: $MODE. Use 'current' or 'target'"
    exit 2
  fi

  test_subnet_naming
  test_f5xc_labels

  # Print summary and exit with appropriate code
  if print_summary; then
    exit 0
  else
    exit 1
  fi
}

# Run main function
main

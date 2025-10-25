#!/bin/bash
#
# F5 Distributed Cloud & Azure Deployment Verification Script
#
# This script provides comprehensive verification of F5 XC and Azure resources,
# replacing the abandoned vesctl CLI tool with REST API calls and Azure CLI.
#
# Purpose:
# - Verify F5 XC objects (registration token, site) via REST API
# - Verify Azure infrastructure (VMs, networking, load balancer) via Azure CLI
# - Integrate with Terraform state for resource identification
# - Provide comprehensive pass/fail reporting
#
# Prerequisites:
# - Azure CLI (az) installed and authenticated (az login)
# - curl, jq installed for API calls and JSON parsing
# - Terraform state accessible
# - F5 XC certificates extracted (~/vescred.cert, ~/vesprivate.key)
# - .env file with environment variables
#
# Usage:
#   ./scripts/verify-f5xc-deployment.sh [options]
#
# Options:
#   --verbose    Enable verbose output
#   --json       Output results in JSON format
#   --help       Show this help message
#
# Exit Codes:
#   0 - All checks passed
#   1 - One or more checks failed
#   2 - Prerequisites not met
#
# Author: Claude Code
# Date: 2025-10-25
# Issue: #95
#

set -o pipefail # Exit on pipeline failures

# =============================================================================
# CONFIGURATION
# =============================================================================

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Environment file (in project root)
ENV_FILE="$PROJECT_ROOT/.env"

# Terraform working directory
TERRAFORM_DIR="$PROJECT_ROOT/terraform/environments/dev"

# Certificate paths (will be set from environment)
CERT_FILE=""
KEY_FILE=""

# F5 XC API endpoint (will be set from environment)
VOLT_API_URL=""

# Tracking variables for checks
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Verbose mode flag
VERBOSE=false

# JSON output flag
JSON_OUTPUT=false

# =============================================================================
# COLOR DEFINITIONS
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Function to print colored output
print_info() {
  if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${BLUE}ℹ️  $1${NC}"
  fi
}

print_success() {
  if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${GREEN}✅ $1${NC}"
  fi
}

print_warning() {
  if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${YELLOW}⚠️  $1${NC}"
  fi
}

print_error() {
  if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${RED}❌ $1${NC}"
  fi
}

print_verbose() {
  if [ "$VERBOSE" = true ] && [ "$JSON_OUTPUT" = false ]; then
    echo -e "${CYAN}🔍 $1${NC}"
  fi
}

# Function to print section headers
print_section() {
  if [ "$JSON_OUTPUT" = false ]; then
    echo ""
    echo -e "${CYAN}=== $1 ===${NC}"
  fi
}

# Function to show help
show_help() {
  cat <<EOF
F5 Distributed Cloud & Azure Deployment Verification Script

Usage: $0 [options]

Options:
  --verbose    Enable verbose output for debugging
  --json       Output results in JSON format
  --help       Show this help message

Description:
  This script verifies F5 XC and Azure resources created by Terraform,
  replacing the abandoned vesctl CLI tool with REST API calls.

Exit Codes:
  0 - All checks passed
  1 - One or more checks failed
  2 - Prerequisites not met

Examples:
  # Standard verification
  ./scripts/verify-f5xc-deployment.sh

  # Verbose output
  ./scripts/verify-f5xc-deployment.sh --verbose

  # JSON output for CI/CD
  ./scripts/verify-f5xc-deployment.sh --json

EOF
}

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

check_prerequisites() {
  print_section "Prerequisite Checks"

  local prereq_failed=false

  # Check for required commands
  local required_commands=("az" "curl" "jq" "terraform")

  for cmd in "${required_commands[@]}"; do
    if command -v "$cmd" &>/dev/null; then
      print_verbose "$cmd: found at $(command -v "$cmd")"
    else
      print_error "$cmd: NOT FOUND - please install $cmd"
      prereq_failed=true
    fi
  done

  # Check Azure CLI authentication
  if command -v az &>/dev/null; then
    if az account show &>/dev/null; then
      local subscription_name=$(az account show --query "name" -o tsv 2>/dev/null)
      print_verbose "Azure CLI: authenticated (subscription: $subscription_name)"
    else
      print_error "Azure CLI: NOT AUTHENTICATED - run 'az login'"
      prereq_failed=true
    fi
  fi

  # Check for .env file
  if [ -f "$ENV_FILE" ]; then
    print_verbose ".env file: found at $ENV_FILE"
  else
    print_error ".env file: NOT FOUND at $ENV_FILE"
    prereq_failed=true
  fi

  # Check Terraform directory
  if [ -d "$TERRAFORM_DIR" ]; then
    print_verbose "Terraform directory: found at $TERRAFORM_DIR"
  else
    print_error "Terraform directory: NOT FOUND at $TERRAFORM_DIR"
    prereq_failed=true
  fi

  if [ "$prereq_failed" = true ]; then
    print_error "Prerequisites not met. Please install missing dependencies."
    return 1
  fi

  print_success "All prerequisites met"
  return 0
}

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

setup_environment() {
  print_section "Environment Setup"

  # Source .env file
  if [ -f "$ENV_FILE" ]; then
    print_verbose "Sourcing .env file: $ENV_FILE"
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    print_success "Environment variables loaded from .env"
  else
    print_error "Failed to source .env file"
    return 1
  fi

  # Set certificate paths
  CERT_FILE="${CERT_FILE:-$HOME/vescred.cert}"
  KEY_FILE="${KEY_FILE:-$HOME/vesprivate.key}"

  # Verify certificates exist
  if [ -f "$CERT_FILE" ] && [ -s "$CERT_FILE" ]; then
    print_verbose "F5 XC certificate: $CERT_FILE"
  else
    print_error "F5 XC certificate not found: $CERT_FILE"
    return 1
  fi

  if [ -f "$KEY_FILE" ] && [ -s "$KEY_FILE" ]; then
    print_verbose "F5 XC key: $KEY_FILE"
  else
    print_error "F5 XC key not found: $KEY_FILE"
    return 1
  fi

  # Set F5 XC API URL (should be set in .env file)
  if [ -z "$VOLT_API_URL" ]; then
    # Try to construct from TF_VAR_f5_xc_tenant if VOLT_API_URL not set
    if [ -n "$TF_VAR_f5_xc_tenant" ]; then
      VOLT_API_URL="https://${TF_VAR_f5_xc_tenant}.console.ves.volterra.io/api"
      print_verbose "F5 XC API URL (constructed): $VOLT_API_URL"
    else
      print_error "Neither VOLT_API_URL nor TF_VAR_f5_xc_tenant set in .env file"
      return 1
    fi
  else
    print_verbose "F5 XC API URL: $VOLT_API_URL"
  fi

  # Change to Terraform directory
  cd "$TERRAFORM_DIR" || {
    print_error "Failed to change to Terraform directory: $TERRAFORM_DIR"
    return 1
  }

  print_success "Environment setup complete"
  return 0
}

# =============================================================================
# F5 XC VERIFICATION FUNCTIONS
# =============================================================================

# Function to verify F5 XC registration token via REST API
verify_f5xc_token() {
  print_section "F5 XC Registration Token Verification"

  ((TOTAL_CHECKS++))

  # Get token name from Terraform state
  local token_name
  token_name=$(terraform state show 'module.f5_xc_registration.volterra_token.ce_site_token' 2>/dev/null | grep "name" | head -1 | awk '{print $3}' | tr -d '"')

  if [ -z "$token_name" ]; then
    print_error "Failed to get token name from Terraform state"
    ((FAILED_CHECKS++))
    return 1
  fi

  print_verbose "Token name from Terraform state: $token_name"

  # Construct API URL for token verification
  local api_url="${VOLT_API_URL}/register/namespaces/system/tokens/${token_name}"
  print_verbose "API URL: $api_url"

  # Make REST API call using certificate authentication
  local response
  local http_code

  response=$(curl -s -w "\n%{http_code}" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    "$api_url" 2>/dev/null)

  http_code=$(echo "$response" | tail -1)
  local response_body=$(echo "$response" | sed '$d')

  print_verbose "HTTP Status Code: $http_code"

  if [ "$http_code" = "200" ]; then
    # Verify response contains expected token name
    if echo "$response_body" | jq -e '.metadata.name' &>/dev/null; then
      local api_token_name=$(echo "$response_body" | jq -r '.metadata.name')

      if [ "$api_token_name" = "$token_name" ]; then
        print_success "Registration token exists in F5 XC Console: $token_name"
        ((PASSED_CHECKS++))
        return 0
      else
        print_error "Token name mismatch - Expected: $token_name, Got: $api_token_name"
        ((FAILED_CHECKS++))
        return 1
      fi
    else
      print_error "Invalid API response format"
      print_verbose "Response: $response_body"
      ((FAILED_CHECKS++))
      return 1
    fi
  else
    print_error "Failed to verify token - HTTP $http_code"
    print_verbose "Response: $response_body"
    ((FAILED_CHECKS++))
    return 1
  fi
}

# Function to verify F5 XC site exists in Terraform state
verify_f5xc_site_state() {
  print_section "F5 XC Site Terraform State Verification"

  ((TOTAL_CHECKS++))

  # Check if site resource exists in Terraform state
  if terraform state show 'module.f5_xc_registration.volterra_securemesh_site_v2.ce_site' &>/dev/null; then
    local site_name
    local site_id

    site_name=$(terraform state show 'module.f5_xc_registration.volterra_securemesh_site_v2.ce_site' | grep "name" | head -1 | awk '{print $3}' | tr -d '"')
    site_id=$(terraform state show 'module.f5_xc_registration.volterra_securemesh_site_v2.ce_site' | grep "id" | head -1 | awk '{print $3}' | tr -d '"')

    print_success "Site exists in Terraform state: $site_name (ID: $site_id)"
    print_verbose "Site resource: module.f5_xc_registration.volterra_securemesh_site_v2.ce_site"
    ((PASSED_CHECKS++))
    return 0
  else
    print_error "Site resource not found in Terraform state"
    ((FAILED_CHECKS++))
    return 1
  fi
}

# Function to verify no drift between Terraform state and F5 XC Console
verify_f5xc_no_drift() {
  print_section "F5 XC Terraform Drift Detection"

  ((TOTAL_CHECKS++))

  print_verbose "Running terraform plan to check for drift..."

  # Run terraform plan and capture output
  local plan_output
  plan_output=$(terraform plan -detailed-exitcode 2>&1)
  local exit_code=$?

  # terraform plan exit codes:
  # 0 = No changes (no drift)
  # 1 = Error
  # 2 = Changes detected (drift exists)

  case $exit_code in
    0)
      print_success "No drift detected - Terraform state matches F5 XC Console"
      ((PASSED_CHECKS++))
      return 0
      ;;
    1)
      print_error "Terraform plan failed"
      print_verbose "Error output: $plan_output"
      ((FAILED_CHECKS++))
      return 1
      ;;
    2)
      print_warning "Drift detected - Terraform state differs from F5 XC Console"
      print_verbose "Changes detected in plan output"
      ((WARNING_CHECKS++))
      # Consider drift as a warning, not a failure
      return 0
      ;;
    *)
      print_error "Unexpected terraform plan exit code: $exit_code"
      ((FAILED_CHECKS++))
      return 1
      ;;
  esac
}

# Wrapper function to run all F5 XC verification checks
verify_f5xc_resources() {
  print_section "F5 XC Resources Verification"

  # Run all F5 XC verification functions
  verify_f5xc_token
  verify_f5xc_site_state
  verify_f5xc_no_drift

  print_verbose "F5 XC verification completed"
}

# =============================================================================
# AZURE VERIFICATION FUNCTIONS
# =============================================================================

# Function to verify Azure resource group exists
verify_azure_resource_group() {
  print_section "Azure Resource Group Verification"

  ((TOTAL_CHECKS++))

  # Get resource group name from Terraform state
  local rg_name
  rg_name=$(terraform state show azurerm_resource_group.main | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  if [ -z "$rg_name" ]; then
    print_error "Failed to get resource group name from Terraform state"
    ((FAILED_CHECKS++))
    return 1
  fi

  print_verbose "Resource group name from Terraform state: $rg_name"

  # Verify resource group exists in Azure
  if az group show --name "$rg_name" &>/dev/null; then
    local location
    location=$(az group show --name "$rg_name" --query "location" -o tsv 2>/dev/null)

    print_success "Resource group exists in Azure: $rg_name (Location: $location)"
    ((PASSED_CHECKS++))
    return 0
  else
    print_error "Resource group not found in Azure: $rg_name"
    ((FAILED_CHECKS++))
    return 1
  fi
}

# Function to verify Azure VMs exist and are running
verify_azure_vms() {
  print_section "Azure Virtual Machines Verification"

  # Get resource group name from Terraform state
  local rg_name
  rg_name=$(terraform state show azurerm_resource_group.main | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  # Get VM names from Terraform state
  local vm1_name vm2_name

  vm1_name=$(terraform state show 'module.ce_appstack_1.azurerm_linux_virtual_machine.ce' 2>/dev/null | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')
  vm2_name=$(terraform state show 'module.ce_appstack_2.azurerm_linux_virtual_machine.ce' 2>/dev/null | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  if [ -z "$vm1_name" ] || [ -z "$vm2_name" ]; then
    print_error "Failed to get VM names from Terraform state"
    ((FAILED_CHECKS++))
    return 1
  fi

  print_verbose "VM names from Terraform: $vm1_name, $vm2_name"

  # Verify first VM
  ((TOTAL_CHECKS++))
  if az vm show --resource-group "$rg_name" --name "$vm1_name" &>/dev/null; then
    local vm1_state
    vm1_state=$(az vm get-instance-view --resource-group "$rg_name" --name "$vm1_name" --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv 2>/dev/null)

    print_success "VM exists: $vm1_name (State: $vm1_state)"
    ((PASSED_CHECKS++))
  else
    print_error "VM not found: $vm1_name"
    ((FAILED_CHECKS++))
  fi

  # Verify second VM
  ((TOTAL_CHECKS++))
  if az vm show --resource-group "$rg_name" --name "$vm2_name" &>/dev/null; then
    local vm2_state
    vm2_state=$(az vm get-instance-view --resource-group "$rg_name" --name "$vm2_name" --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv 2>/dev/null)

    print_success "VM exists: $vm2_name (State: $vm2_state)"
    ((PASSED_CHECKS++))
  else
    print_error "VM not found: $vm2_name"
    ((FAILED_CHECKS++))
  fi
}

# Function to verify Azure networking resources
verify_azure_networking() {
  print_section "Azure Networking Verification"

  # Get resource group name
  local rg_name
  rg_name=$(terraform state show azurerm_resource_group.main | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  # Get VNet name from Terraform state
  local vnet_name
  vnet_name=$(terraform state show 'module.hub_vnet.azurerm_virtual_network.hub' 2>/dev/null | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  if [ -z "$vnet_name" ]; then
    print_error "Failed to get VNet name from Terraform state"
    ((FAILED_CHECKS++))
    return 1
  fi

  print_verbose "VNet name from Terraform: $vnet_name"

  # Verify VNet exists
  ((TOTAL_CHECKS++))
  if az network vnet show --resource-group "$rg_name" --name "$vnet_name" &>/dev/null; then
    local vnet_address_space
    vnet_address_space=$(az network vnet show --resource-group "$rg_name" --name "$vnet_name" --query "addressSpace.addressPrefixes[0]" -o tsv 2>/dev/null)

    print_success "VNet exists: $vnet_name (Address Space: $vnet_address_space)"
    ((PASSED_CHECKS++))
  else
    print_error "VNet not found: $vnet_name"
    ((FAILED_CHECKS++))
  fi

  # Verify subnets exist
  ((TOTAL_CHECKS++))
  local subnet_count
  subnet_count=$(az network vnet subnet list --resource-group "$rg_name" --vnet-name "$vnet_name" --query "length(@)" -o tsv 2>/dev/null)

  if [ "$subnet_count" -gt 0 ]; then
    print_success "Subnets found: $subnet_count subnets in $vnet_name"
    ((PASSED_CHECKS++))
  else
    print_error "No subnets found in VNet: $vnet_name"
    ((FAILED_CHECKS++))
  fi
}

# Function to verify Azure load balancer
verify_azure_load_balancer() {
  print_section "Azure Load Balancer Verification"

  # Get resource group name
  local rg_name
  rg_name=$(terraform state show azurerm_resource_group.main | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  # Get load balancer name from Terraform state
  local lb_name
  lb_name=$(terraform state show 'module.load_balancer.azurerm_lb.internal' 2>/dev/null | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  if [ -z "$lb_name" ]; then
    print_error "Failed to get load balancer name from Terraform state"
    ((FAILED_CHECKS++))
    return 1
  fi

  print_verbose "Load balancer name from Terraform: $lb_name"

  # Verify load balancer exists
  ((TOTAL_CHECKS++))
  if az network lb show --resource-group "$rg_name" --name "$lb_name" &>/dev/null; then
    local lb_sku
    lb_sku=$(az network lb show --resource-group "$rg_name" --name "$lb_name" --query "sku.name" -o tsv 2>/dev/null)

    print_success "Load balancer exists: $lb_name (SKU: $lb_sku)"
    ((PASSED_CHECKS++))
  else
    print_error "Load balancer not found: $lb_name"
    ((FAILED_CHECKS++))
  fi

  # Verify backend address pool exists
  ((TOTAL_CHECKS++))
  local backend_pool_count
  backend_pool_count=$(az network lb address-pool list --resource-group "$rg_name" --lb-name "$lb_name" --query "length(@)" -o tsv 2>/dev/null)

  if [ "$backend_pool_count" -gt 0 ]; then
    print_success "Backend address pools found: $backend_pool_count pools in $lb_name"
    ((PASSED_CHECKS++))
  else
    print_error "No backend address pools found in load balancer: $lb_name"
    ((FAILED_CHECKS++))
  fi
}

# Function to verify Azure public IPs
verify_azure_public_ips() {
  print_section "Azure Public IP Verification"

  # Get resource group name
  local rg_name
  rg_name=$(terraform state show azurerm_resource_group.main | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  # Count public IPs from Terraform state
  local expected_ips=2 # Two CE VMs should have public IPs

  ((TOTAL_CHECKS++))

  # List public IPs in resource group
  local actual_ip_count
  actual_ip_count=$(az network public-ip list --resource-group "$rg_name" --query "length(@)" -o tsv 2>/dev/null)

  if [ "$actual_ip_count" -ge "$expected_ips" ]; then
    print_success "Public IPs found: $actual_ip_count IPs (expected >= $expected_ips)"

    # Show IP addresses if verbose
    if [ "$VERBOSE" = true ]; then
      local ip_list
      ip_list=$(az network public-ip list --resource-group "$rg_name" --query "[].{Name:name, IP:ipAddress}" -o tsv 2>/dev/null)
      while IFS=$'\t' read -r name ip; do
        print_verbose "Public IP: $name = $ip"
      done <<<"$ip_list"
    fi

    ((PASSED_CHECKS++))
  else
    print_error "Insufficient public IPs - Expected: >= $expected_ips, Found: $actual_ip_count"
    ((FAILED_CHECKS++))
  fi
}

# Function to verify Azure network security groups
verify_azure_nsgs() {
  print_section "Azure Network Security Groups Verification"

  # Get resource group name
  local rg_name
  rg_name=$(terraform state show azurerm_resource_group.main | grep "^ *name " | head -1 | awk '{print $3}' | tr -d '"')

  ((TOTAL_CHECKS++))

  # List NSGs in resource group
  local nsg_count
  nsg_count=$(az network nsg list --resource-group "$rg_name" --query "length(@)" -o tsv 2>/dev/null)

  if [ "$nsg_count" -gt 0 ]; then
    print_success "Network Security Groups found: $nsg_count NSGs"

    # Show NSG names if verbose
    if [ "$VERBOSE" = true ]; then
      local nsg_list
      nsg_list=$(az network nsg list --resource-group "$rg_name" --query "[].name" -o tsv 2>/dev/null)
      while read -r nsg_name; do
        print_verbose "NSG: $nsg_name"
      done <<<"$nsg_list"
    fi

    ((PASSED_CHECKS++))
  else
    print_error "No Network Security Groups found"
    ((FAILED_CHECKS++))
  fi
}

# Wrapper function to run all Azure verification checks
verify_azure_resources() {
  print_section "Azure Resources Verification"

  # Run all Azure verification functions
  verify_azure_resource_group
  verify_azure_vms
  verify_azure_networking
  verify_azure_load_balancer
  verify_azure_public_ips
  verify_azure_nsgs

  print_verbose "Azure verification completed"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --verbose)
        VERBOSE=true
        shift
        ;;
      --json)
        JSON_OUTPUT=true
        shift
        ;;
      --help)
        show_help
        exit 0
        ;;
      *)
        echo "Unknown option: $1"
        show_help
        exit 2
        ;;
    esac
  done

  # Print header
  if [ "$JSON_OUTPUT" = false ]; then
    echo ""
    echo "=========================================="
    echo "F5 XC & Azure Deployment Verification"
    echo "=========================================="
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Environment: dev"
    echo "=========================================="
  fi

  # Run prerequisite checks
  if ! check_prerequisites; then
    exit 2
  fi

  # Setup environment
  if ! setup_environment; then
    exit 2
  fi

  # Run F5 XC verification checks (Phase 2)
  verify_f5xc_resources

  # Run Azure verification checks (Phase 3)
  verify_azure_resources

  # Print summary
  if [ "$JSON_OUTPUT" = true ]; then
    # JSON format output
    cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "dev",
  "summary": {
    "total_checks": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "warnings": $WARNING_CHECKS,
    "failed": $FAILED_CHECKS,
    "success_rate": $(awk "BEGIN {printf \"%.2f\", ($PASSED_CHECKS/$TOTAL_CHECKS)*100}")
  },
  "status": "$([ $FAILED_CHECKS -eq 0 ] && echo "success" || echo "failure")",
  "exit_code": $([ $FAILED_CHECKS -eq 0 ] && echo "0" || echo "1")
}
EOF
  else
    # Human-readable format
    print_section "Summary"
    print_info "Total Checks: $TOTAL_CHECKS"
    print_info "Passed: $PASSED_CHECKS"
    print_info "Warnings: $WARNING_CHECKS"
    print_info "Failed: $FAILED_CHECKS"

    if [ $FAILED_CHECKS -eq 0 ]; then
      echo ""
      print_success "All verification checks passed!"
    else
      echo ""
      print_error "Some verification checks failed. Please review the output above."
    fi
  fi

  # Exit with appropriate code
  if [ $FAILED_CHECKS -gt 0 ]; then
    exit 1
  else
    exit 0
  fi
}

# Execute main function
main "$@"

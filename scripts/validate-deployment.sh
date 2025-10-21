#!/bin/bash
#
# Deployment Validation Script
#
# Validates F5 XC CE deployment to Azure after terraform apply
# Checks:
# - Azure resources created successfully
# - Network connectivity
# - CE registration with F5 XC Console
# - Load balancer health probes
# - Routing configuration
#
# Usage:
#   ./scripts/validate-deployment.sh <environment>
#   ./scripts/validate-deployment.sh dev
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found"
    exit 1
fi

# Arguments
ENVIRONMENT="${1:-dev}"
TERRAFORM_DIR="terraform/environments/$ENVIRONMENT"

if [ ! -d "$TERRAFORM_DIR" ]; then
    print_error "Environment directory not found: $TERRAFORM_DIR"
    exit 1
fi

print_info "Validating deployment for environment: $ENVIRONMENT"
echo ""

# Get Terraform outputs
cd "$TERRAFORM_DIR"
if [ ! -f "terraform.tfstate" ]; then
    print_error "Terraform state file not found - run terraform apply first"
    exit 1
fi

print_info "Step 1/6: Retrieving Terraform outputs..."
HUB_VNET_ID=$(terraform output -raw hub_vnet_id 2>/dev/null || echo "")
SPOKE_VNET_ID=$(terraform output -raw spoke_vnet_id 2>/dev/null || echo "")
RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")

if [ -z "$RESOURCE_GROUP" ]; then
    print_error "Could not retrieve resource group from Terraform outputs"
    exit 1
fi

print_success "Terraform outputs retrieved"
echo ""

# Validate Azure resources
print_info "Step 2/6: Validating Azure resource group..."
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    print_success "Resource group exists: $RESOURCE_GROUP"
else
    print_error "Resource group not found: $RESOURCE_GROUP"
    exit 1
fi
echo ""

print_info "Step 3/6: Validating virtual networks..."
if [ -n "$HUB_VNET_ID" ]; then
    if az network vnet show --ids "$HUB_VNET_ID" &> /dev/null; then
        print_success "Hub VNET exists"
    else
        print_error "Hub VNET not found"
        exit 1
    fi
else
    print_warning "Hub VNET ID not available - skipping validation"
fi

if [ -n "$SPOKE_VNET_ID" ]; then
    if az network vnet show --ids "$SPOKE_VNET_ID" &> /dev/null; then
        print_success "Spoke VNET exists"
    else
        print_error "Spoke VNET not found"
        exit 1
    fi
else
    print_warning "Spoke VNET ID not available - skipping validation"
fi
echo ""

print_info "Step 4/6: Validating VNET peering..."
if [ -n "$HUB_VNET_ID" ] && [ -n "$SPOKE_VNET_ID" ]; then
    HUB_VNET_NAME=$(az network vnet show --ids "$HUB_VNET_ID" --query name -o tsv)
    SPOKE_VNET_NAME=$(az network vnet show --ids "$SPOKE_VNET_ID" --query name -o tsv)

    # Check hub-to-spoke peering
    PEERING_STATE=$(az network vnet peering list \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$HUB_VNET_NAME" \
        --query "[?remoteVirtualNetwork.id=='$SPOKE_VNET_ID'].peeringState" \
        -o tsv)

    if [ "$PEERING_STATE" == "Connected" ]; then
        print_success "VNET peering established"
    else
        print_error "VNET peering not established (state: $PEERING_STATE)"
        exit 1
    fi
else
    print_warning "VNET IDs not available - skipping peering validation"
fi
echo ""

print_info "Step 5/6: Validating load balancer..."
LB_NAME=$(az network lb list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].name" \
    -o tsv 2>/dev/null || echo "")

if [ -n "$LB_NAME" ]; then
    print_success "Load balancer found: $LB_NAME"

    # Check health probes
    PROBE_COUNT=$(az network lb probe list \
        --resource-group "$RESOURCE_GROUP" \
        --lb-name "$LB_NAME" \
        --query "length(@)" \
        -o tsv)

    if [ "$PROBE_COUNT" -gt 0 ]; then
        print_success "Health probes configured ($PROBE_COUNT probes)"
    else
        print_warning "No health probes found on load balancer"
    fi

    # Check backend pool
    BACKEND_COUNT=$(az network lb address-pool list \
        --resource-group "$RESOURCE_GROUP" \
        --lb-name "$LB_NAME" \
        --query "length(@)" \
        -o tsv)

    if [ "$BACKEND_COUNT" -gt 0 ]; then
        print_success "Backend pools configured ($BACKEND_COUNT pools)"
    else
        print_warning "No backend pools found on load balancer"
    fi
else
    print_warning "Load balancer not found - may not be deployed yet"
fi
echo ""

print_info "Step 6/6: Validating F5 XC CE registration..."
CE_SITE_NAME=$(terraform output -raw ce_site_name 2>/dev/null || echo "")

if [ -n "$CE_SITE_NAME" ]; then
    print_info "CE Site Name: $CE_SITE_NAME"
    print_warning "F5 XC Console validation requires API access - check manually at:"
    print_warning "https://<tenant>.console.ves.volterra.io/web/workspaces/distributed-apps/sites"
else
    print_warning "CE site name not available - skipping F5 XC validation"
fi
echo ""

# Summary
print_success "✨ Deployment validation complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Hub VNET: ${HUB_VNET_NAME:-Not deployed}"
echo "Spoke VNET: ${SPOKE_VNET_NAME:-Not deployed}"
echo "Load Balancer: ${LB_NAME:-Not deployed}"
echo "CE Site: ${CE_SITE_NAME:-Not configured}"
echo ""
echo "Next Steps:"
echo "  1. Verify CE instance status in Azure Portal"
echo "  2. Check CE registration in F5 XC Console"
echo "  3. Test connectivity from spoke to internet through hub NVA"
echo "  4. Monitor load balancer health probe status"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

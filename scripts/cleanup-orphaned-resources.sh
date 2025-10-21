#!/bin/bash
#
# Orphaned Resources Cleanup Script
#
# Identifies and optionally removes orphaned Azure resources that may be left
# after failed terraform destroy operations or manual deletions.
#
# Resources checked:
# - Network interfaces without VM attachment
# - Public IPs not associated with resources
# - Disks not attached to VMs
# - Empty resource groups
# - Network security groups not associated with subnets
#
# Usage:
#   ./scripts/cleanup-orphaned-resources.sh --dry-run   # List only
#   ./scripts/cleanup-orphaned-resources.sh --delete    # Delete orphaned resources
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

if ! az account show &> /dev/null; then
    print_error "Not logged in to Azure. Run: az login"
    exit 1
fi

# Arguments
MODE="${1:---dry-run}"
RESOURCE_GROUP_PATTERN="${2:-xc-ce-}"

if [ "$MODE" != "--dry-run" ] && [ "$MODE" != "--delete" ]; then
    print_error "Invalid mode. Use --dry-run or --delete"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

print_info "Subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"
print_info "Resource Group Pattern: $RESOURCE_GROUP_PATTERN"
print_info "Mode: $MODE"
echo ""

if [ "$MODE" == "--delete" ]; then
    print_warning "⚠️  DELETE MODE - Resources will be removed!"
    echo ""
    read -p "Continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy](es)?$ ]]; then
        print_info "Cancelled by user"
        exit 0
    fi
    echo ""
fi

# Track orphaned resources
ORPHANED_COUNT=0

# 1. Find orphaned network interfaces
print_info "Checking for orphaned network interfaces..."
ORPHANED_NICS=$(az network nic list \
    --query "[?virtualMachine==null && name contains '$RESOURCE_GROUP_PATTERN'].{Name:name, ResourceGroup:resourceGroup}" \
    -o tsv)

if [ -n "$ORPHANED_NICS" ]; then
    while IFS=$'\t' read -r nic_name rg_name; do
        ORPHANED_COUNT=$((ORPHANED_COUNT + 1))
        print_warning "Found orphaned NIC: $nic_name (RG: $rg_name)"

        if [ "$MODE" == "--delete" ]; then
            az network nic delete --name "$nic_name" --resource-group "$rg_name" --yes --no-wait
            print_success "Deleted: $nic_name"
        fi
    done <<< "$ORPHANED_NICS"
else
    print_success "No orphaned NICs found"
fi
echo ""

# 2. Find orphaned public IPs
print_info "Checking for orphaned public IPs..."
ORPHANED_IPS=$(az network public-ip list \
    --query "[?ipConfiguration==null && name contains '$RESOURCE_GROUP_PATTERN'].{Name:name, ResourceGroup:resourceGroup}" \
    -o tsv)

if [ -n "$ORPHANED_IPS" ]; then
    while IFS=$'\t' read -r ip_name rg_name; do
        ORPHANED_COUNT=$((ORPHANED_COUNT + 1))
        print_warning "Found orphaned Public IP: $ip_name (RG: $rg_name)"

        if [ "$MODE" == "--delete" ]; then
            az network public-ip delete --name "$ip_name" --resource-group "$rg_name" --yes --no-wait
            print_success "Deleted: $ip_name"
        fi
    done <<< "$ORPHANED_IPS"
else
    print_success "No orphaned Public IPs found"
fi
echo ""

# 3. Find unattached disks
print_info "Checking for unattached managed disks..."
ORPHANED_DISKS=$(az disk list \
    --query "[?managedBy==null && name contains '$RESOURCE_GROUP_PATTERN'].{Name:name, ResourceGroup:resourceGroup}" \
    -o tsv)

if [ -n "$ORPHANED_DISKS" ]; then
    while IFS=$'\t' read -r disk_name rg_name; do
        ORPHANED_COUNT=$((ORPHANED_COUNT + 1))
        print_warning "Found unattached disk: $disk_name (RG: $rg_name)"

        if [ "$MODE" == "--delete" ]; then
            az disk delete --name "$disk_name" --resource-group "$rg_name" --yes --no-wait
            print_success "Deleted: $disk_name"
        fi
    done <<< "$ORPHANED_DISKS"
else
    print_success "No unattached disks found"
fi
echo ""

# 4. Find orphaned NSGs
print_info "Checking for orphaned network security groups..."
ORPHANED_NSGS=$(az network nsg list \
    --query "[?subnets==null && networkInterfaces==null && name contains '$RESOURCE_GROUP_PATTERN'].{Name:name, ResourceGroup:resourceGroup}" \
    -o tsv)

if [ -n "$ORPHANED_NSGS" ]; then
    while IFS=$'\t' read -r nsg_name rg_name; do
        ORPHANED_COUNT=$((ORPHANED_COUNT + 1))
        print_warning "Found orphaned NSG: $nsg_name (RG: $rg_name)"

        if [ "$MODE" == "--delete" ]; then
            az network nsg delete --name "$nsg_name" --resource-group "$rg_name" --yes --no-wait
            print_success "Deleted: $nsg_name"
        fi
    done <<< "$ORPHANED_NSGS"
else
    print_success "No orphaned NSGs found"
fi
echo ""

# 5. Find empty resource groups
print_info "Checking for empty resource groups..."
RESOURCE_GROUPS=$(az group list --query "[?name contains '$RESOURCE_GROUP_PATTERN'].name" -o tsv)

for rg in $RESOURCE_GROUPS; do
    RESOURCE_COUNT=$(az resource list --resource-group "$rg" --query "length(@)" -o tsv)

    if [ "$RESOURCE_COUNT" -eq 0 ]; then
        ORPHANED_COUNT=$((ORPHANED_COUNT + 1))
        print_warning "Found empty resource group: $rg"

        if [ "$MODE" == "--delete" ]; then
            az group delete --name "$rg" --yes --no-wait
            print_success "Deleted: $rg"
        fi
    fi
done

if [ -z "$RESOURCE_GROUPS" ]; then
    print_success "No matching resource groups found"
fi
echo ""

# Summary
if [ "$MODE" == "--dry-run" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Dry Run Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    if [ $ORPHANED_COUNT -gt 0 ]; then
        print_warning "Found $ORPHANED_COUNT orphaned resource(s)"
        echo ""
        echo "To delete these resources, run:"
        echo "  $0 --delete"
    else
        print_success "No orphaned resources found"
    fi
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Cleanup Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    if [ $ORPHANED_COUNT -gt 0 ]; then
        print_success "Deleted $ORPHANED_COUNT orphaned resource(s)"
        echo ""
        echo "Note: Deletion operations are running asynchronously (--no-wait)"
        echo "Check Azure Portal to verify completion"
    else
        print_success "No orphaned resources found"
    fi
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

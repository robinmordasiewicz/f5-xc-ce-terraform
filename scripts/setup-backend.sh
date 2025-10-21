#!/bin/bash
#
# Azure Backend Setup Script for Terraform State
#
# This script creates the Azure infrastructure required for Terraform remote state:
# - Resource group for Terraform state
# - Storage account with encryption and HTTPS-only access
# - Blob container with versioning
# - Soft delete protection
# - Azure AD app registration for GitHub Actions (optional)
# - Workload identity federation credentials (optional)
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - Contributor access to Azure subscription
# - jq installed for JSON parsing
#
# Usage:
#   ./scripts/setup-backend.sh
#   ./scripts/setup-backend.sh --create-service-principal
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

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v az &>/dev/null; then
  print_error "Azure CLI not found. Please install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
  exit 1
fi

if ! command -v jq &>/dev/null; then
  print_warning "jq not found. Install for better JSON parsing: brew install jq (macOS) or apt-get install jq (Linux)"
fi

# Check if logged in to Azure
if ! az account show &>/dev/null; then
  print_warning "Not currently logged in to Azure"
  echo ""
  print_info "To continue, you need to authenticate with Azure"
  print_info "This will open a browser window for you to sign in"
  echo ""
  read -p "Press Enter to open Azure login in your browser, or Ctrl+C to cancel: " -r
  echo ""

  print_info "Initiating Azure login..."
  if az login; then
    print_success "Successfully logged in to Azure"
  else
    print_error "Azure login failed. Please check your credentials and try again"
    exit 1
  fi
  echo ""
else
  print_success "Already logged in to Azure"
fi

print_success "Prerequisites check passed"

# Get current subscription and user info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
AZURE_USERNAME=$(az account show --query user.name -o tsv | cut -d@ -f1 | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-')

# GitHub repository name
GITHUB_REPO="f5-xc-ce-terraform"

# Configuration with improved naming to prevent conflicts
# Azure resource group naming: alphanumeric + hyphens, max 90 chars
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-${AZURE_USERNAME}-${GITHUB_REPO}-tfstate}"
LOCATION="${LOCATION:-eastus}"
# Storage account: lowercase alphanumeric only, 3-24 chars, globally unique
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-tfstate${AZURE_USERNAME}$(date +%s)}"
CONTAINER_NAME="${CONTAINER_NAME:-tfstate}"
CREATE_SP="${1:-}"

print_info "Target Subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"
print_info "Resource Group: $RESOURCE_GROUP"
print_info "Location: $LOCATION"
print_info "Storage Account: $STORAGE_ACCOUNT"
print_info "Container: $CONTAINER_NAME"
echo ""

read -p "Continue with these settings? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy](es)?$ ]]; then
  print_warning "Setup cancelled by user"
  exit 0
fi

echo ""
print_info "Step 1/5: Creating resource group..."

if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
  print_warning "Resource group '$RESOURCE_GROUP' already exists"
else
  az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags environment=shared managed_by=terraform purpose=state-storage owner="$AZURE_USERNAME" project="$GITHUB_REPO" \
    --output none
  print_success "Resource group created: $RESOURCE_GROUP"
fi

echo ""
print_info "Step 2/5: Creating storage account..."

if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  print_warning "Storage account '$STORAGE_ACCOUNT' already exists"
else
  az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --encryption-services blob \
    --https-only true \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --tags environment=shared managed_by=terraform purpose=state-storage owner="$AZURE_USERNAME" project="$GITHUB_REPO" \
    --output none
  print_success "Storage account created: $STORAGE_ACCOUNT"
fi

echo ""
print_info "Step 3/5: Creating blob container..."

if az storage container show --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT" &>/dev/null 2>&1; then
  print_warning "Container '$CONTAINER_NAME' already exists"
else
  az storage container create \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode login \
    --output none
  print_success "Blob container created: $CONTAINER_NAME"
fi

echo ""
print_info "Step 4/5: Configuring blob service properties..."

# Enable versioning
az storage account blob-service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --enable-versioning true \
  --output none
print_success "Blob versioning enabled"

# Enable soft delete (30 days retention)
az storage account blob-service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --enable-delete-retention true \
  --delete-retention-days 30 \
  --output none
print_success "Soft delete enabled (30-day retention)"

# Enable container soft delete
az storage account blob-service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --enable-container-delete-retention true \
  --container-delete-retention-days 30 \
  --output none
print_success "Container soft delete enabled (30-day retention)"

echo ""
print_info "Step 5/5: Configuring access..."

# Get current user object ID for RBAC assignment
CURRENT_USER_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")

if [ -n "$CURRENT_USER_ID" ]; then
  # Assign Storage Blob Data Owner to current user
  if az role assignment list --assignee "$CURRENT_USER_ID" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" --role "Storage Blob Data Owner" --query '[].id' -o tsv | grep -q .; then
    print_warning "Current user already has Storage Blob Data Owner role"
  else
    az role assignment create \
      --role "Storage Blob Data Owner" \
      --assignee "$CURRENT_USER_ID" \
      --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
      --output none
    print_success "Assigned Storage Blob Data Owner role to current user"
  fi
else
  print_warning "Could not determine current user ID - skipping RBAC assignment"
fi

# Create service principal for GitHub Actions (optional)
if [ "$CREATE_SP" == "--create-service-principal" ]; then
  echo ""
  print_info "Creating Azure AD App Registration for GitHub Actions..."

  APP_NAME="GitHub-Actions-F5-XC-CE"

  # Check if app already exists
  APP_ID=$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv 2>/dev/null || echo "")

  if [ -n "$APP_ID" ]; then
    print_warning "App registration '$APP_NAME' already exists with ID: $APP_ID"
  else
    APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
    print_success "App registration created: $APP_NAME ($APP_ID)"

    # Create service principal
    az ad sp create --id "$APP_ID" --output none
    print_success "Service principal created"
  fi

  # Assign Contributor role at subscription level
  if az role assignment list --assignee "$APP_ID" --scope "/subscriptions/$SUBSCRIPTION_ID" --role "Contributor" --query '[].id' -o tsv | grep -q .; then
    print_warning "Service principal already has Contributor role"
  else
    az role assignment create \
      --role "Contributor" \
      --assignee "$APP_ID" \
      --scope "/subscriptions/$SUBSCRIPTION_ID" \
      --output none
    print_success "Assigned Contributor role to service principal"
  fi

  # Assign Storage Blob Data Owner for state file access
  if az role assignment list --assignee "$APP_ID" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" --role "Storage Blob Data Owner" --query '[].id' -o tsv | grep -q .; then
    print_warning "Service principal already has Storage Blob Data Owner role"
  else
    az role assignment create \
      --role "Storage Blob Data Owner" \
      --assignee "$APP_ID" \
      --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
      --output none
    print_success "Assigned Storage Blob Data Owner role for state access"
  fi

  echo ""
  print_info "To configure GitHub Actions workload identity federation, run:"
  echo ""
  echo "export APP_ID=\"$APP_ID\""
  echo "export GITHUB_ORG=\"your-github-org\""
  echo "export GITHUB_REPO=\"f5-xc-ce-terraform\""
  echo ""
  echo "az ad app federated-credential create --id \$APP_ID --parameters '{\"name\":\"github-actions-main\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"repo:\$GITHUB_ORG/\$GITHUB_REPO:ref:refs/heads/main\",\"audiences\":[\"api://AzureADTokenExchange\"]}'"
  echo ""
  echo "az ad app federated-credential create --id \$APP_ID --parameters '{\"name\":\"github-actions-pr\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"repo:\$GITHUB_ORG/\$GITHUB_REPO:pull_request\",\"audiences\":[\"api://AzureADTokenExchange\"]}'"
  echo ""
fi

# Summary
echo ""
print_success "✨ Azure backend setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SAVE THESE VALUES - Required for Terraform and GitHub Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Backend Configuration (for terraform init):"
echo "  ARM_RESOURCE_GROUP_NAME=\"$RESOURCE_GROUP\""
echo "  ARM_STORAGE_ACCOUNT_NAME=\"$STORAGE_ACCOUNT\""
echo "  ARM_CONTAINER_NAME=\"$CONTAINER_NAME\""
echo "  ARM_KEY=\"terraform.tfstate\""
echo ""
echo "Azure Credentials (for GitHub Secrets):"
echo "  AZURE_SUBSCRIPTION_ID=\"$SUBSCRIPTION_ID\""
echo "  AZURE_TENANT_ID=\"$TENANT_ID\""
if [ -n "$APP_ID" ]; then
  echo "  AZURE_CLIENT_ID=\"$APP_ID\""
fi
echo ""
echo "Next Steps:"
echo "  1. Add these values to GitHub Secrets in your repository"
echo "  2. Configure workload identity federation (if using service principal)"
echo "  3. Get F5 XC API token and add as F5_XC_API_TOKEN secret"
echo "  4. Run terraform init to verify backend configuration"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

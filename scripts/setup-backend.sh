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

# GitHub repository info (auto-detect from git remote)
GITHUB_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [ -n "$GITHUB_REMOTE" ]; then
  GITHUB_ORG=$(echo "$GITHUB_REMOTE" | sed -n 's/.*[:/]\([^/]*\)\/[^/]*$/\1/p')
  GITHUB_REPO=$(echo "$GITHUB_REMOTE" | sed -n 's/.*\/\([^/]*\)\.git$/\1/p')
else
  GITHUB_ORG="${GITHUB_ORG:-}"
  GITHUB_REPO="${GITHUB_REPO:-f5-xc-ce-terraform}"
fi

# Configuration with improved naming to prevent conflicts
# Azure resource group naming: alphanumeric + hyphens, max 90 chars
RESOURCE_GROUP="${RESOURCE_GROUP:-${AZURE_USERNAME}-${GITHUB_REPO}-tfstate}"
LOCATION="${LOCATION:-eastus}"
# Storage account: lowercase alphanumeric only, 3-24 chars, globally unique
# Use hash of username for uniqueness, add 'tf' suffix = max 24 chars
USER_HASH=$(echo -n "${AZURE_USERNAME}" | md5sum | cut -c1-22)
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-${USER_HASH}tf}"
# Container: lowercase alphanumeric + hyphens, 3-63 chars, add '-tf' suffix
CONTAINER_BASE=$(echo -n "${AZURE_USERNAME}-${GITHUB_REPO}" | tr '[:upper:]' '[:lower:]')
CONTAINER_NAME="${CONTAINER_NAME:-$(echo $CONTAINER_BASE | cut -c1-60)-tf}"

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
print_info "Step 1/8: Creating resource group..."

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
print_info "Step 2/8: Creating storage account..."

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
print_info "Step 3/8: Creating blob container..."

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
print_info "Step 4/8: Configuring blob service properties..."

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
print_info "Step 5/8: Configuring access..."

# Get current user object ID for RBAC assignment
CURRENT_USER_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")

if [ -n "$CURRENT_USER_ID" ]; then
  # Assign Storage Blob Data Owner to current user
  if az role assignment list --assignee "$CURRENT_USER_ID" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" --role "Storage Blob Data Owner" --query '[].id' -o tsv 2>/dev/null | grep -q .; then
    print_warning "Current user already has Storage Blob Data Owner role"
  else
    if az role assignment create \
      --role "Storage Blob Data Owner" \
      --assignee "$CURRENT_USER_ID" \
      --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
      --output none 2>/dev/null; then
      print_success "Assigned Storage Blob Data Owner role to current user"
    else
      print_warning "Failed to assign Storage Blob Data Owner role (insufficient permissions)"
      print_info "Please ask your Azure administrator to assign this role manually"
    fi
  fi
else
  print_warning "Could not determine current user ID - skipping RBAC assignment"
fi

# Create service principal for GitHub Actions (mandatory for OIDC)
echo ""
print_info "Step 6/8: Creating Azure AD App Registration for GitHub Actions..."

APP_NAME="GitHub-Actions-${GITHUB_REPO}"

# Check if app already exists (idempotent)
APP_ID=$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv 2>/dev/null || echo "")

if [ -n "$APP_ID" ]; then
  print_warning "App registration '$APP_NAME' already exists with ID: $APP_ID"
else
  if APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv 2>/dev/null); then
    print_success "App registration created: $APP_NAME ($APP_ID)"
  else
    print_error "Failed to create app registration (insufficient permissions)"
    print_info "Please ask your Azure administrator to create the app registration"
    print_info "Skipping service principal and OIDC configuration"
    APP_ID=""
  fi
fi

# Create service principal if it doesn't exist (idempotent)
if [ -n "$APP_ID" ]; then
  if az ad sp show --id "$APP_ID" &>/dev/null; then
    print_warning "Service principal already exists"
  else
    if az ad sp create --id "$APP_ID" --output none 2>/dev/null; then
      print_success "Service principal created"
    else
      print_error "Failed to create service principal (insufficient permissions)"
      print_info "Please ask your Azure administrator to create the service principal"
      APP_ID=""
    fi
  fi
fi

# Only configure roles and OIDC if we have a service principal
if [ -n "$APP_ID" ]; then
  # Assign Contributor role at subscription level (idempotent)
  if az role assignment list --assignee "$APP_ID" --scope "/subscriptions/$SUBSCRIPTION_ID" --role "Contributor" --query '[].id' -o tsv 2>/dev/null | grep -q .; then
    print_warning "Service principal already has Contributor role"
  else
    if az role assignment create \
      --role "Contributor" \
      --assignee "$APP_ID" \
      --scope "/subscriptions/$SUBSCRIPTION_ID" \
      --output none 2>/dev/null; then
      print_success "Assigned Contributor role to service principal"
    else
      print_warning "Failed to assign Contributor role (insufficient permissions)"
      print_info "Please ask your Azure administrator to assign this role manually"
    fi
  fi

  # Assign Storage Blob Data Owner for state file access (idempotent)
  if az role assignment list --assignee "$APP_ID" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" --role "Storage Blob Data Owner" --query '[].id' -o tsv 2>/dev/null | grep -q .; then
    print_warning "Service principal already has Storage Blob Data Owner role"
  else
    if az role assignment create \
      --role "Storage Blob Data Owner" \
      --assignee "$APP_ID" \
      --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
      --output none 2>/dev/null; then
      print_success "Assigned Storage Blob Data Owner role for state access"
    else
      print_warning "Failed to assign Storage Blob Data Owner role (insufficient permissions)"
      print_info "Please ask your Azure administrator to assign this role manually"
    fi
  fi

  # Configure OIDC federated credentials for GitHub Actions
  echo ""
  print_info "Step 7/8: Configuring OIDC federated credentials..."

  if [ -z "$GITHUB_ORG" ]; then
    print_error "GitHub organization not detected. Please set GITHUB_ORG environment variable"
    exit 1
  fi

  # Federated credential for main branch (idempotent)
  CRED_NAME_MAIN="github-actions-main"
  if az ad app federated-credential show --id "$APP_ID" --federated-credential-id "$CRED_NAME_MAIN" &>/dev/null; then
    print_warning "Federated credential '$CRED_NAME_MAIN' already exists"
  else
    az ad app federated-credential create --id "$APP_ID" --parameters "{
      \"name\": \"$CRED_NAME_MAIN\",
      \"issuer\": \"https://token.actions.githubusercontent.com\",
      \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/main\",
      \"audiences\": [\"api://AzureADTokenExchange\"]
    }" --output none
    print_success "Created federated credential for main branch"
  fi

  # Federated credential for pull requests (idempotent)
  CRED_NAME_PR="github-actions-pr"
  if az ad app federated-credential show --id "$APP_ID" --federated-credential-id "$CRED_NAME_PR" &>/dev/null; then
    print_warning "Federated credential '$CRED_NAME_PR' already exists"
  else
    az ad app federated-credential create --id "$APP_ID" --parameters "{
      \"name\": \"$CRED_NAME_PR\",
      \"issuer\": \"https://token.actions.githubusercontent.com\",
      \"subject\": \"repo:$GITHUB_ORG/$GITHUB_REPO:pull_request\",
      \"audiences\": [\"api://AzureADTokenExchange\"]
    }" --output none
    print_success "Created federated credential for pull requests"
  fi
else
  echo ""
  print_warning "Skipping role assignments and OIDC configuration (no service principal)"
fi

# Create GitHub secrets
echo ""
print_info "Step 8/8: Creating GitHub secrets..."

if ! command -v gh &>/dev/null; then
  print_warning "GitHub CLI (gh) not found. Skipping GitHub secrets creation"
  print_info "Install gh CLI: https://cli.github.com/"
else
  # Check if authenticated to GitHub
  if ! gh auth status &>/dev/null; then
    print_warning "Not authenticated to GitHub. Skipping secrets creation"
    print_info "Run: gh auth login"
  else
    # Set secrets (idempotent - gh secret set overwrites if exists)
    echo "$SUBSCRIPTION_ID" | gh secret set AZURE_SUBSCRIPTION_ID --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set AZURE_SUBSCRIPTION_ID secret" || print_warning "Failed to set AZURE_SUBSCRIPTION_ID"

    echo "$TENANT_ID" | gh secret set AZURE_TENANT_ID --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set AZURE_TENANT_ID secret" || print_warning "Failed to set AZURE_TENANT_ID"

    echo "$APP_ID" | gh secret set AZURE_CLIENT_ID --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set AZURE_CLIENT_ID secret" || print_warning "Failed to set AZURE_CLIENT_ID"

    echo "$RESOURCE_GROUP" | gh secret set ARM_RESOURCE_GROUP_NAME --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set ARM_RESOURCE_GROUP_NAME secret" || print_warning "Failed to set ARM_RESOURCE_GROUP_NAME"

    echo "$STORAGE_ACCOUNT" | gh secret set ARM_STORAGE_ACCOUNT_NAME --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set ARM_STORAGE_ACCOUNT_NAME secret" || print_warning "Failed to set ARM_STORAGE_ACCOUNT_NAME"

    echo "$CONTAINER_NAME" | gh secret set ARM_CONTAINER_NAME --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set ARM_CONTAINER_NAME secret" || print_warning "Failed to set ARM_CONTAINER_NAME"

    echo "terraform.tfstate" | gh secret set ARM_KEY --repo "$GITHUB_ORG/$GITHUB_REPO" 2>/dev/null &&
      print_success "Set ARM_KEY secret" || print_warning "Failed to set ARM_KEY"
  fi
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

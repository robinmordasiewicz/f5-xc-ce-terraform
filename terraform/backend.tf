# Terraform Remote State Backend Configuration
#
# Azure Blob Storage backend with encryption, versioning, and state locking
# via lease mechanism. This configuration is used across all environments.
#
# Prerequisites:
# 1. Azure Storage Account created (see scripts/setup-backend.sh)
# 2. GitHub Actions configured with workload identity federation
# 3. Service principal has "Storage Blob Data Owner" role on container
#
# State File Security:
# - Encryption at rest: Azure Storage Service Encryption (SSE)
# - Encryption in transit: HTTPS only (enforced at storage account level)
# - Access control: Azure RBAC + storage account firewall rules
# - Versioning: Enabled on blob container for state history
# - Soft delete: 30-day retention for accidental deletion protection

terraform {
  backend "azurerm" {
    # Storage account configuration
    # These values are set via environment variables in GitHub Actions:
    # - ARM_RESOURCE_GROUP_NAME
    # - ARM_STORAGE_ACCOUNT_NAME
    # - ARM_CONTAINER_NAME
    # - ARM_KEY (state file name)

    # For local development, create backend.local.tfvars:
    # resource_group_name  = "terraform-state-rg"
    # storage_account_name = "tfstatexcce"
    # container_name       = "tfstate"
    # key                  = "001-ce-cicd-automation.tfstate"

    # Authentication via workload identity federation (GitHub Actions)
    use_oidc = true

    # State locking via Azure Blob lease mechanism
    # Automatically enabled when using azurerm backend
  }
}

# Example backend configuration for local development:
# terraform init -backend-config=backend.local.tfvars
#
# Example backend configuration in GitHub Actions:
# - name: Terraform Init
#   run: terraform init
#   env:
#     ARM_RESOURCE_GROUP_NAME: "terraform-state-rg"
#     ARM_STORAGE_ACCOUNT_NAME: "tfstatexcce"
#     ARM_CONTAINER_NAME: "tfstate"
#     ARM_KEY: "001-ce-cicd-automation.tfstate"
#     ARM_USE_OIDC: "true"
#     ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
#     ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
#     ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

terraform {
  required_version = ">= 1.6.0"

  # Azure Remote State Backend
  # Configuration values provided via backend.local.hcl (manual CLI)
  # or environment variables (GitHub Actions OIDC)
  backend "azurerm" {
    # Values set via:
    # - backend.local.hcl: resource_group_name, storage_account_name, container_name, key
    # - Environment variables: ARM_RESOURCE_GROUP_NAME, ARM_STORAGE_ACCOUNT_NAME, etc.
    # - Authentication: Azure CLI (az login) or OIDC (ARM_USE_OIDC=true)
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }

    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.45"
    }

    volterra = {
      source  = "volterraedge/volterra"
      version = "~> 0.11"
    }
  }
}

provider "azurerm" {
  features {}

  # GitHub Actions workload identity federation (OIDC)
  use_oidc = true
}

provider "azuread" {
  # Inherits authentication from azurerm provider
  use_oidc = true
}

provider "volterra" {
  # Authentication via environment variables:
  # - VOLT_API_KEY: API token/key for authentication
  # - VOLT_API_URL: Tenant API endpoint
  #
  # For CI/CD: Provided via GitHub secrets
  # For Manual CLI: Sourced from .env file
  #
  # Variables passed through TF_VAR_* for Terraform input variables:
  # - TF_VAR_f5_xc_api_token → var.f5_xc_api_token → VOLT_API_KEY
  # - TF_VAR_f5_xc_tenant → var.f5_xc_tenant → URL construction

  api_key = var.f5_xc_api_token
  url     = "https://${var.f5_xc_tenant}.console.ves.volterra.io/api"
}

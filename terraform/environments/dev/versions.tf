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

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
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
  # Authentication via P12 Certificate (environment variables):
  #
  # REQUIRED environment variables:
  #   VES_P12_CONTENT  - Base64-encoded P12 certificate bundle
  #   VES_P12_PASSWORD - P12 certificate password
  #   VOLT_API_URL     - Tenant API endpoint
  #
  # How to obtain P12 certificate:
  #   1. Login to F5 XC Console: https://<tenant>.console.ves.volterra.io
  #   2. Navigate to: Administration → Personal Management → Credentials
  #   3. Click: Add Credentials → API Certificate (NOT API Token!)
  #   4. Download .p12 file and save the password
  #   5. Base64 encode: base64 -i certificate.p12 | tr -d '\n'
  #   6. Set environment variables in .env file
  #
  # For CI/CD: Set VES_P12_CONTENT and VES_P12_PASSWORD as GitHub secrets
  # For Manual CLI: Source from .env file (see .env.example)
  #
  # NOTE: API tokens are NOT supported by the Terraform provider.
  #       You must use certificate-based authentication (P12 or cert/key pair).
}

# F5 XC CE AppStack Module
# CE Secure Mesh Site deployment (hub NVA)
# Implementation in Phase 3 (User Story 1)

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    volterra = {
      source  = "volterraedge/volterra"
      version = "~> 0.11"
    }
  }
}

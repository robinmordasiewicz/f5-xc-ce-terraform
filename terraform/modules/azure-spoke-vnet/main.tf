# Azure Spoke VNET Module
# Creates spoke virtual network with routing to hub NVA
# Implementation in Phase 3 (User Story 1)

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

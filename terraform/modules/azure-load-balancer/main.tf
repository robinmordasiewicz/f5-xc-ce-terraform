# Azure Load Balancer Module
# Internal load balancer for CE NVA high availability
# Implementation in Phase 3 (User Story 1)

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

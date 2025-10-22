# F5 XC CE Managed Kubernetes Module
# CE K8s deployment in spoke VNET
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

# F5 XC Registration Module
# CE site creation and registration with F5 XC Console
# Implementation in Phase 3 (User Story 1)

terraform {
  required_providers {
    volterra = {
      source  = "volterraedge/volterra"
      version = "~> 0.11"
    }
  }
}

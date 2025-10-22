# TFLint Configuration
# Terraform linting for code quality and best practices
# See: https://github.com/terraform-linters/tflint

config {
  # Enable module inspection
  module = true

  # Force initialization (download plugins)
  force = false

  # Disable module color output
  disabled_by_default = false
}

# Azure Provider Plugin
plugin "azurerm" {
  enabled = true
  version = "0.25.1"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# Terraform Core Rules
plugin "terraform" {
  enabled = true
  version = "0.5.0"
  source  = "github.com/terraform-linters/tflint-ruleset-terraform"

  preset = "recommended"
}

# Rule Overrides
# --------------

# Enforce naming conventions
rule "terraform_naming_convention" {
  enabled = true

  # Variable naming: snake_case
  variable {
    format = "snake_case"
  }

  # Resource naming: snake_case
  resource {
    format = "snake_case"
  }

  # Module naming: snake_case
  module {
    format = "snake_case"
  }

  # Output naming: snake_case
  output {
    format = "snake_case"
  }
}

# Require variable descriptions
rule "terraform_documented_variables" {
  enabled = true
}

# Require output descriptions
rule "terraform_documented_outputs" {
  enabled = true
}

# Enforce variable type declarations
rule "terraform_typed_variables" {
  enabled = true
}

# Disallow deprecated syntax
rule "terraform_deprecated_index" {
  enabled = true
}

# Disallow deprecated interpolation
rule "terraform_deprecated_interpolation" {
  enabled = true
}

# Require module version constraints
rule "terraform_module_pinned_source" {
  enabled = true
}

# Standard module structure
rule "terraform_standard_module_structure" {
  enabled = true
}

# Azure-specific rules
# --------------------

# Enforce VM naming conventions
rule "azurerm_virtual_machine_name" {
  enabled = true
}

# Enforce resource group naming
rule "azurerm_resource_group_name" {
  enabled = true
}

# Enforce VNET naming
rule "azurerm_virtual_network_name" {
  enabled = true
}

# Enforce subnet naming
rule "azurerm_subnet_name" {
  enabled = true
}

# Disabled rules (with justification)
# -----------------------------------

# Allow unused declarations during development
rule "terraform_unused_declarations" {
  enabled = false
}

# Allow required providers in modules (we declare in versions.tf)
rule "terraform_required_providers" {
  enabled = false
}

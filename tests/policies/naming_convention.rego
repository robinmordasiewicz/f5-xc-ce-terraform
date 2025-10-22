# Terraform Compliance Policy: Naming Conventions
# Enforces snake_case naming for all Terraform resources and outputs
# Constitution compliance: Code Quality Standards

package terraform.naming

import future.keywords.in

# Resource naming convention: snake_case
deny[msg] {
    resource := input.resource_changes[_]
    name := resource.name
    not is_snake_case(name)
    msg := sprintf("Resource '%s' does not follow snake_case naming convention", [name])
}

# Output naming convention: snake_case
deny[msg] {
    output := input.planned_values.outputs[name]
    not is_snake_case(name)
    msg := sprintf("Output '%s' does not follow snake_case naming convention", [name])
}

# Variable naming convention: snake_case
deny[msg] {
    variable := input.variables[name]
    not is_snake_case(name)
    msg := sprintf("Variable '%s' does not follow snake_case naming convention", [name])
}

# Azure resource naming conventions
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_virtual_network"
    name := resource.change.after.name
    contains(name, "_")  # Azure VNETs should use hyphens, not underscores
    msg := sprintf("Azure VNET '%s' should use hyphens (-) instead of underscores (_)", [name])
}

deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_subnet"
    name := resource.change.after.name
    contains(name, "_")  # Azure subnets should use hyphens, not underscores
    msg := sprintf("Azure Subnet '%s' should use hyphens (-) instead of underscores (_)", [name])
}

# Resource group naming: should include environment
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_resource_group"
    name := resource.change.after.name
    not contains(name, "-dev-")
    not contains(name, "-prod-")
    not contains(name, "-staging-")
    msg := sprintf("Resource group '%s' should include environment indicator (dev/prod/staging)", [name])
}

# Helper function to check snake_case
is_snake_case(name) {
    regex.match("^[a-z][a-z0-9_]*$", name)
}

# Tag requirements
deny[msg] {
    resource := input.resource_changes[_]
    startswith(resource.type, "azurerm_")
    tags := object.get(resource.change.after, "tags", {})
    not tags.environment
    msg := sprintf("Resource '%s' missing required tag: environment", [resource.address])
}

deny[msg] {
    resource := input.resource_changes[_]
    startswith(resource.type, "azurerm_")
    tags := object.get(resource.change.after, "tags", {})
    not tags.managed_by
    msg := sprintf("Resource '%s' missing required tag: managed_by", [resource.address])
}

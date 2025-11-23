# Outputs for Azure Hub VNET Module
# Updated for 3-NIC CE Architecture

output "vnet_id" {
  description = "ID of the hub virtual network"
  value       = azurerm_virtual_network.hub.id
}

output "vnet_name" {
  description = "Name of the hub virtual network"
  value       = azurerm_virtual_network.hub.name
}

output "address_space" {
  description = "Address space of the hub VNET"
  value       = azurerm_virtual_network.hub.address_space
}

# Management Subnet Outputs
output "mgmt_subnet_id" {
  description = "ID of the management subnet"
  value       = azurerm_subnet.mgmt.id
}

output "mgmt_subnet_address_prefix" {
  description = "Address prefix of the management subnet"
  value       = var.mgmt_subnet_prefix
}

output "nsg_mgmt_id" {
  description = "ID of the management subnet NSG"
  value       = azurerm_network_security_group.mgmt.id
}

# External Subnet Outputs
output "external_subnet_id" {
  description = "ID of the external subnet"
  value       = azurerm_subnet.external.id
}

output "external_subnet_address_prefix" {
  description = "Address prefix of the external subnet"
  value       = var.external_subnet_prefix
}

output "nsg_external_id" {
  description = "ID of the external subnet NSG"
  value       = azurerm_network_security_group.external.id
}

# Internal Subnet Outputs
output "internal_subnet_id" {
  description = "ID of the internal subnet"
  value       = azurerm_subnet.internal.id
}

output "internal_subnet_address_prefix" {
  description = "Address prefix of the internal subnet"
  value       = var.internal_subnet_prefix
}

output "nsg_internal_id" {
  description = "ID of the internal subnet NSG"
  value       = azurerm_network_security_group.internal.id
}

# Route Table Outputs
output "route_table_id" {
  description = "ID of the hub route table"
  value       = azurerm_route_table.hub.id
}

# Legacy outputs for backward compatibility (will be removed)
output "nva_subnet_id" {
  description = "DEPRECATED: Use external_subnet_id instead"
  value       = azurerm_subnet.external.id
}

output "nva_subnet_address_prefix" {
  description = "DEPRECATED: Use external_subnet_address_prefix instead"
  value       = var.external_subnet_prefix
}

output "nsg_nva_id" {
  description = "DEPRECATED: Use nsg_external_id instead"
  value       = azurerm_network_security_group.external.id
}

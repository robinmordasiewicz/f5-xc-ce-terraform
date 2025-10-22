# Outputs for Azure Hub VNET Module

output "vnet_id" {
  description = "ID of the hub virtual network"
  value       = azurerm_virtual_network.hub.id
}

output "vnet_name" {
  description = "Name of the hub virtual network"
  value       = azurerm_virtual_network.hub.name
}

output "nva_subnet_id" {
  description = "ID of the NVA subnet"
  value       = azurerm_subnet.nva.id
}

output "nva_subnet_address_prefix" {
  description = "Address prefix of the NVA subnet"
  value       = var.nva_subnet_prefix
}

output "mgmt_subnet_id" {
  description = "ID of the management subnet"
  value       = azurerm_subnet.mgmt.id
}

output "address_space" {
  description = "Address space of the hub VNET"
  value       = azurerm_virtual_network.hub.address_space
}

output "nsg_nva_id" {
  description = "ID of the NVA subnet NSG"
  value       = azurerm_network_security_group.nva.id
}

output "nsg_mgmt_id" {
  description = "ID of the management subnet NSG"
  value       = azurerm_network_security_group.mgmt.id
}

output "route_table_id" {
  description = "ID of the hub route table"
  value       = azurerm_route_table.hub.id
}

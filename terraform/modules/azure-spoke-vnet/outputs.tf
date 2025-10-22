# Outputs for Azure Spoke VNET Module

output "vnet_id" {
  description = "ID of the spoke virtual network"
  value       = azurerm_virtual_network.spoke.id
}

output "vnet_name" {
  description = "Name of the spoke virtual network"
  value       = azurerm_virtual_network.spoke.name
}

output "workload_subnet_id" {
  description = "ID of the workload subnet"
  value       = azurerm_subnet.workload.id
}

output "peering_id" {
  description = "ID of the VNET peering (spoke to hub)"
  value       = azurerm_virtual_network_peering.spoke_to_hub.id
}

output "peering_status" {
  description = "Status of the VNET peering (ID indicates peering exists)"
  value       = azurerm_virtual_network_peering.spoke_to_hub.id
}

output "route_table_id" {
  description = "ID of the spoke route table"
  value       = azurerm_route_table.spoke.id
}

output "default_route_next_hop" {
  description = "Next hop IP for default route (hub NVA)"
  value       = var.hub_nva_ip
}

output "nsg_id" {
  description = "ID of the workload subnet NSG"
  value       = azurerm_network_security_group.workload.id
}

# Outputs for Azure Hub VNET Module

output "vnet_id" {
  description = "ID of the hub virtual network"
  value       = "" # Implementation in Phase 3
}

output "vnet_name" {
  description = "Name of the hub virtual network"
  value       = var.vnet_name
}

output "nva_subnet_id" {
  description = "ID of the NVA subnet"
  value       = "" # Implementation in Phase 3
}

output "mgmt_subnet_id" {
  description = "ID of the management subnet"
  value       = "" # Implementation in Phase 3
}

output "address_space" {
  description = "Address space of the hub VNET"
  value       = var.address_space
}

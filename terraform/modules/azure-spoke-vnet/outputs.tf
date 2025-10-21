# Outputs for Azure Spoke VNET Module

output "vnet_id" {
  description = "ID of the spoke virtual network"
  value       = "" # Implementation in Phase 3
}

output "vnet_name" {
  description = "Name of the spoke virtual network"
  value       = var.vnet_name
}

output "workload_subnet_id" {
  description = "ID of the workload subnet"
  value       = "" # Implementation in Phase 3
}

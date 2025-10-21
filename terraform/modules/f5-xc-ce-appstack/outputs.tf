# Outputs for F5 XC CE AppStack Module

output "vm_id" {
  description = "ID of the CE VM"
  value       = azurerm_linux_virtual_machine.ce.id
}

output "vm_name" {
  description = "Name of the CE VM"
  value       = azurerm_linux_virtual_machine.ce.name
}

output "private_ip" {
  description = "Private IP address of CE"
  value       = azurerm_network_interface.ce.private_ip_address
}

output "public_ip" {
  description = "Public IP address of CE (for management)"
  value       = azurerm_public_ip.ce_mgmt.ip_address
}

output "identity_id" {
  description = "ID of the managed identity"
  value       = azurerm_user_assigned_identity.ce.id
}

output "identity_principal_id" {
  description = "Principal ID of the managed identity"
  value       = azurerm_user_assigned_identity.ce.principal_id
}

output "nic_id" {
  description = "ID of the network interface"
  value       = azurerm_network_interface.ce.id
}

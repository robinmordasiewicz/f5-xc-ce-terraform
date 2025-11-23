# Outputs for F5 XC CE AppStack Module (3-NIC Architecture)

output "vm_id" {
  description = "ID of the CE VM"
  value       = azurerm_linux_virtual_machine.ce.id
}

output "vm_name" {
  description = "Name of the CE VM"
  value       = azurerm_linux_virtual_machine.ce.name
}

# Management NIC outputs
output "mgmt_private_ip" {
  description = "Private IP address of CE management NIC"
  value       = azurerm_network_interface.ce_mgmt.private_ip_address
}

output "public_ip" {
  description = "Public IP address of CE (for management access)"
  value       = azurerm_public_ip.ce_mgmt.ip_address
}

output "mgmt_nic_id" {
  description = "ID of the management network interface"
  value       = azurerm_network_interface.ce_mgmt.id
}

# External NIC outputs
output "external_private_ip" {
  description = "Private IP address of CE external NIC"
  value       = azurerm_network_interface.ce_external.private_ip_address
}

output "external_nic_id" {
  description = "ID of the external network interface"
  value       = azurerm_network_interface.ce_external.id
}

# Internal NIC outputs
output "internal_private_ip" {
  description = "Private IP address of CE internal NIC"
  value       = azurerm_network_interface.ce_internal.private_ip_address
}

output "internal_nic_id" {
  description = "ID of the internal network interface"
  value       = azurerm_network_interface.ce_internal.id
}

# Identity outputs
output "identity_id" {
  description = "ID of the managed identity"
  value       = azurerm_user_assigned_identity.ce.id
}

output "identity_principal_id" {
  description = "Principal ID of the managed identity"
  value       = azurerm_user_assigned_identity.ce.principal_id
}

# Legacy compatibility - maps to management NIC
output "private_ip" {
  description = "Private IP address of CE (legacy - maps to mgmt NIC)"
  value       = azurerm_network_interface.ce_mgmt.private_ip_address
}

output "nic_id" {
  description = "ID of the network interface (legacy - maps to mgmt NIC)"
  value       = azurerm_network_interface.ce_mgmt.id
}

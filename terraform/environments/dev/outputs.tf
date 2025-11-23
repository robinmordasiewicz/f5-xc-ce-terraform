# Outputs for F5 XC CE Development Environment (3-NIC Architecture)

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

# Hub VNET Outputs
output "hub_vnet_id" {
  description = "ID of the hub virtual network"
  value       = module.hub_vnet.vnet_id
}

output "hub_vnet_name" {
  description = "Name of the hub virtual network"
  value       = module.hub_vnet.vnet_name
}

output "hub_mgmt_subnet_id" {
  description = "ID of the management subnet"
  value       = module.hub_vnet.mgmt_subnet_id
}

output "hub_external_subnet_id" {
  description = "ID of the external subnet"
  value       = module.hub_vnet.external_subnet_id
}

output "hub_internal_subnet_id" {
  description = "ID of the internal subnet"
  value       = module.hub_vnet.internal_subnet_id
}

# Spoke VNET Outputs
output "spoke_vnet_id" {
  description = "ID of the spoke virtual network"
  value       = module.spoke_vnet.vnet_id
}

output "spoke_vnet_name" {
  description = "Name of the spoke virtual network"
  value       = module.spoke_vnet.vnet_name
}

output "peering_status" {
  description = "Status of VNET peering"
  value       = module.spoke_vnet.peering_status
}

# External Load Balancer Outputs (Public)
output "external_lb_id" {
  description = "ID of the external load balancer"
  value       = module.external_lb.lb_id
}

output "external_lb_public_ip" {
  description = "Public IP address of the external load balancer"
  value       = module.external_lb.public_ip_address
}

# Internal Load Balancer Outputs (Spoke Routing)
output "internal_lb_id" {
  description = "ID of the internal load balancer"
  value       = module.internal_lb.lb_id
}

output "internal_lb_frontend_ip" {
  description = "Frontend private IP of the internal load balancer"
  value       = module.internal_lb.frontend_ip
}

# F5 XC Registration Outputs (2 Independent Sites)
output "ce_site_1_name" {
  description = "F5 XC CE site 1 name"
  value       = module.f5_xc_registration_1.site_name
}

output "ce_site_1_id" {
  description = "F5 XC CE site 1 ID"
  value       = module.f5_xc_registration_1.site_id
}

output "ce_site_2_name" {
  description = "F5 XC CE site 2 name"
  value       = module.f5_xc_registration_2.site_name
}

output "ce_site_2_id" {
  description = "F5 XC CE site 2 ID"
  value       = module.f5_xc_registration_2.site_id
}

# CE Instance 1 Outputs (3-NIC)
output "ce_vm_1_name" {
  description = "Name of CE instance 1"
  value       = module.ce_appstack_1.vm_name
}

output "ce_vm_1_mgmt_ip" {
  description = "Management NIC private IP of CE instance 1"
  value       = module.ce_appstack_1.mgmt_private_ip
}

output "ce_vm_1_external_ip" {
  description = "External NIC private IP of CE instance 1"
  value       = module.ce_appstack_1.external_private_ip
}

output "ce_vm_1_internal_ip" {
  description = "Internal NIC private IP of CE instance 1"
  value       = module.ce_appstack_1.internal_private_ip
}

output "ce_vm_1_public_ip" {
  description = "Public IP of CE instance 1 (management)"
  value       = module.ce_appstack_1.public_ip
}

# CE Instance 2 Outputs (3-NIC)
output "ce_vm_2_name" {
  description = "Name of CE instance 2"
  value       = module.ce_appstack_2.vm_name
}

output "ce_vm_2_mgmt_ip" {
  description = "Management NIC private IP of CE instance 2"
  value       = module.ce_appstack_2.mgmt_private_ip
}

output "ce_vm_2_external_ip" {
  description = "External NIC private IP of CE instance 2"
  value       = module.ce_appstack_2.external_private_ip
}

output "ce_vm_2_internal_ip" {
  description = "Internal NIC private IP of CE instance 2"
  value       = module.ce_appstack_2.internal_private_ip
}

output "ce_vm_2_public_ip" {
  description = "Public IP of CE instance 2 (management)"
  value       = module.ce_appstack_2.public_ip
}

# Routing Outputs
output "default_route_next_hop" {
  description = "Next hop for default route from spoke (Internal LB IP)"
  value       = module.spoke_vnet.default_route_next_hop
}

# SSH Key Outputs
output "ssh_key_generated" {
  description = "Whether SSH key was auto-generated (true) or user-provided (false)"
  value       = var.ssh_public_key == ""
}

output "ssh_private_key" {
  description = "Auto-generated SSH private key for CE VM access (only if auto-generated)"
  value       = var.ssh_public_key == "" ? tls_private_key.ce_ssh[0].private_key_openssh : "User provided their own SSH key"
  sensitive   = true
}

output "ssh_connection_instructions" {
  description = "Instructions for SSH access to CE VMs"
  value       = var.ssh_public_key == "" ? "SSH key was auto-generated. To connect to CE VMs:\n\n1. Save the private key:\n   terraform output -raw ssh_private_key > ce_ssh_key.pem\n   chmod 600 ce_ssh_key.pem\n\n2. Connect to CE VM 1:\n   ssh -i ce_ssh_key.pem ceadmin@${module.ce_appstack_1.public_ip}\n\n3. Connect to CE VM 2:\n   ssh -i ce_ssh_key.pem ceadmin@${module.ce_appstack_2.public_ip}\n\nNote: The private key is also stored in the Terraform state file." : "Using user-provided SSH key. Use your own private key to connect."
}

# Summary Output
output "deployment_summary" {
  description = "Deployment summary"
  value = {
    resource_group     = azurerm_resource_group.main.name
    hub_vnet           = module.hub_vnet.vnet_name
    spoke_vnet         = module.spoke_vnet.vnet_name
    external_lb        = module.external_lb.lb_name
    external_lb_ip     = module.external_lb.public_ip_address
    internal_lb        = module.internal_lb.lb_name
    internal_lb_ip     = module.internal_lb.frontend_ip
    ce_site_1          = module.f5_xc_registration_1.site_name
    ce_site_2          = module.f5_xc_registration_2.site_name
    ce_instances       = [module.ce_appstack_1.vm_name, module.ce_appstack_2.vm_name]
    peering_status     = module.spoke_vnet.peering_status
    ssh_key_status     = var.ssh_public_key == "" ? "auto-generated" : "user-provided"
    architecture       = "3-NIC per CE (Mgmt, External, Internal)"
    load_balancer_type = "Dual LB (External Public + Internal HA Ports)"
  }
}

# Outputs for F5 XC CE Development Environment

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

output "hub_nva_subnet_id" {
  description = "ID of the NVA subnet"
  value       = module.hub_vnet.nva_subnet_id
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

# Load Balancer Outputs
output "load_balancer_id" {
  description = "ID of the load balancer"
  value       = module.load_balancer.lb_id
}

output "lb_health_probe_port" {
  description = "Load balancer health probe port"
  value       = module.load_balancer.health_probe_port
}

# F5 XC Registration Outputs
output "ce_site_name" {
  description = "F5 XC CE site name"
  value       = module.f5_xc_registration.site_name
}

output "ce_site_id" {
  description = "F5 XC CE site ID"
  value       = module.f5_xc_registration.site_id
}

# CE Instance Outputs
output "ce_vm_1_name" {
  description = "Name of CE instance 1"
  value       = module.ce_appstack_1.vm_name
}

output "ce_vm_1_private_ip" {
  description = "Private IP of CE instance 1"
  value       = module.ce_appstack_1.private_ip
}

output "ce_vm_1_public_ip" {
  description = "Public IP of CE instance 1"
  value       = module.ce_appstack_1.public_ip
}

output "ce_vm_2_name" {
  description = "Name of CE instance 2"
  value       = module.ce_appstack_2.vm_name
}

output "ce_vm_2_private_ip" {
  description = "Private IP of CE instance 2"
  value       = module.ce_appstack_2.private_ip
}

output "ce_vm_2_public_ip" {
  description = "Public IP of CE instance 2"
  value       = module.ce_appstack_2.public_ip
}

# Routing Outputs
output "default_route_next_hop" {
  description = "Next hop for default route from spoke"
  value       = module.spoke_vnet.default_route_next_hop
}

# Summary Output
output "deployment_summary" {
  description = "Deployment summary"
  value = {
    resource_group = azurerm_resource_group.main.name
    hub_vnet       = module.hub_vnet.vnet_name
    spoke_vnet     = module.spoke_vnet.vnet_name
    load_balancer  = module.load_balancer.lb_name
    ce_site        = module.f5_xc_registration.site_name
    ce_instances   = [module.ce_appstack_1.vm_name, module.ce_appstack_2.vm_name]
    peering_status = module.spoke_vnet.peering_status
  }
}

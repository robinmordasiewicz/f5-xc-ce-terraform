# Outputs for Azure External Load Balancer Module

output "lb_id" {
  description = "ID of the external load balancer"
  value       = azurerm_lb.external.id
}

output "lb_name" {
  description = "Name of the external load balancer"
  value       = azurerm_lb.external.name
}

output "backend_pool_id" {
  description = "ID of the backend address pool"
  value       = azurerm_lb_backend_address_pool.external.id
}

output "public_ip_id" {
  description = "ID of the public IP address"
  value       = azurerm_public_ip.external_lb.id
}

output "public_ip_address" {
  description = "Public IP address of the load balancer"
  value       = azurerm_public_ip.external_lb.ip_address
}

output "health_probe_id" {
  description = "ID of the TCP health probe"
  value       = azurerm_lb_probe.tcp.id
}

output "health_probe_port" {
  description = "Health probe port"
  value       = var.health_probe_port
}

output "frontend_ip_configuration_name" {
  description = "Name of the frontend IP configuration"
  value       = "external-frontend"
}

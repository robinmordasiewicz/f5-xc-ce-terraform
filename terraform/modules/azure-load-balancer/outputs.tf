# Outputs for Azure Internal Load Balancer Module

output "lb_id" {
  description = "ID of the internal load balancer"
  value       = azurerm_lb.internal.id
}

output "lb_name" {
  description = "Name of the internal load balancer"
  value       = azurerm_lb.internal.name
}

output "backend_pool_id" {
  description = "ID of the backend address pool"
  value       = azurerm_lb_backend_address_pool.internal.id
}

output "frontend_ip" {
  description = "Frontend private IP address of the load balancer"
  value       = var.frontend_ip_address
}

output "health_probe_id" {
  description = "ID of the TCP health probe"
  value       = azurerm_lb_probe.tcp.id
}

output "health_probe_port" {
  description = "Port for TCP health probe"
  value       = var.health_probe_port
}

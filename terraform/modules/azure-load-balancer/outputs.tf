# Outputs for Azure Load Balancer Module

output "lb_id" {
  description = "ID of the load balancer"
  value       = azurerm_lb.internal.id
}

output "lb_name" {
  description = "Name of the load balancer"
  value       = azurerm_lb.internal.name
}

output "backend_pool_id" {
  description = "ID of the backend address pool"
  value       = azurerm_lb_backend_address_pool.ce_pool.id
}

output "frontend_ip" {
  description = "Frontend IP address of the load balancer"
  value       = var.frontend_ip_address
}

output "health_probe_tcp_id" {
  description = "ID of the TCP health probe"
  value       = azurerm_lb_probe.ce_tcp.id
}

output "health_probe_https_id" {
  description = "ID of the HTTPS health probe"
  value       = azurerm_lb_probe.ce_https.id
}

output "health_probe_port" {
  description = "Port for TCP health probe"
  value       = "65500"
}

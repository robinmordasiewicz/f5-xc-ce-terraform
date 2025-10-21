# Outputs for Azure Load Balancer Module

output "lb_id" {
  description = "ID of the load balancer"
  value       = "" # Implementation in Phase 3
}

output "backend_pool_id" {
  description = "ID of the backend address pool"
  value       = "" # Implementation in Phase 3
}

output "frontend_ip" {
  description = "Frontend IP address of the load balancer"
  value       = var.frontend_ip_address
}

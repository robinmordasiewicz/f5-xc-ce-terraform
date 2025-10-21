# Outputs for F5 XC Registration Module

output "registration_token" {
  description = "CE registration token for cloud-init configuration"
  value       = data.volterra_registration_token.ce_token.token
  sensitive   = true
}

output "site_id" {
  description = "F5 XC CE site ID"
  value       = volterra_azure_vnet_site.ce_site.id
}

output "site_name" {
  description = "F5 XC CE site name"
  value       = volterra_azure_vnet_site.ce_site.name
}

output "namespace" {
  description = "F5 XC namespace"
  value       = var.namespace
}

# Variables for F5 XC CE AppStack Module

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "vm_name" {
  description = "Name of the CE VM"
  type        = string
}

variable "vm_size" {
  description = "Size of the CE VM (minimum Standard_D8s_v3: 8 vCPUs, 32 GB RAM)"
  type        = string
  default     = "Standard_D8s_v3"
}

variable "subnet_id" {
  description = "ID of the subnet for CE deployment"
  type        = string
}

variable "registration_token" {
  description = "F5 XC registration token"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for CE access"
  type        = string
}

variable "lb_backend_pool_id" {
  description = "ID of the load balancer backend pool"
  type        = string
}

variable "availability_zone" {
  description = "Availability zone for VM deployment (1, 2, or 3)"
  type        = string
  default     = "1"
}

variable "enable_accelerated_networking" {
  description = "Enable accelerated networking for better performance"
  type        = bool
  default     = true
}

variable "admin_username" {
  description = "Admin username for CE VM"
  type        = string
  default     = "ceadmin"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

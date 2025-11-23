# Variables for F5 XC CE AppStack Module (3-NIC Architecture)

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

# Subnet IDs for 3-NIC configuration
variable "mgmt_subnet_id" {
  description = "ID of the management subnet (for RE tunnel, SSH, F5 XC console)"
  type        = string
}

variable "external_subnet_id" {
  description = "ID of the external subnet (for External LB backend)"
  type        = string
}

variable "internal_subnet_id" {
  description = "ID of the internal subnet (for Internal LB backend)"
  type        = string
}

variable "registration_token" {
  description = "F5 XC registration token"
  type        = string
  sensitive   = true
}

variable "site_name" {
  description = "F5 XC site name - unique per CE for independent vsites"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key for CE access"
  type        = string
}

# Load Balancer backend pool IDs
variable "external_lb_backend_pool_id" {
  description = "ID of the external load balancer backend pool"
  type        = string
}

variable "internal_lb_backend_pool_id" {
  description = "ID of the internal load balancer backend pool"
  type        = string
}

variable "availability_zone" {
  description = "Availability zone for VM deployment (1, 2, or 3)"
  type        = string
  default     = "1"
}

variable "enable_accelerated_networking" {
  description = "Enable accelerated networking. NOTE: Must be false for F5 XC CE VMs - accelerated networking creates bonded interfaces that fail VPM certified hardware check"
  type        = bool
  default     = false
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

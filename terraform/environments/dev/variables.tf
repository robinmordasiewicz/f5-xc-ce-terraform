# Variables for F5 XC CE Development Environment

variable "azure_region" {
  description = "Azure region for resource deployment"
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "prefix" {
  description = "Prefix for F5 XC CE workload resources (not used for hub infrastructure)"
  type        = string
  default     = "f5-xc-ce"
}

# Hub VNET Configuration
variable "hub_vnet_address_space" {
  description = "Address space for hub VNET"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "hub_nva_subnet_prefix" {
  description = "Address prefix for NVA subnet (minimum /26)"
  type        = string
  default     = "10.0.1.0/26"
}

variable "hub_mgmt_subnet_prefix" {
  description = "Address prefix for management subnet"
  type        = string
  default     = "10.0.2.0/24"
}

# Spoke VNET Configuration
variable "spoke_vnet_address_space" {
  description = "Address space for spoke VNET"
  type        = list(string)
  default     = ["10.1.0.0/16"]
}

variable "spoke_workload_subnet_prefix" {
  description = "Address prefix for workload subnet"
  type        = string
  default     = "10.1.1.0/24"
}

# Load Balancer Configuration
variable "lb_frontend_ip" {
  description = "Static frontend IP for internal load balancer"
  type        = string
  default     = "10.0.1.4"
}

variable "hub_nva_ip" {
  description = "IP address of hub NVA (for spoke routing)"
  type        = string
  default     = "10.0.1.4"
}

# F5 XC Configuration
variable "f5_xc_namespace" {
  description = "F5 XC namespace"
  type        = string
  default     = "system"
}

variable "f5_xc_tenant" {
  description = "F5 XC tenant name"
  type        = string
}

# CE Configuration
variable "ce_site_size" {
  description = "F5 XC CE site size - determines Azure VM SKU and resource allocation (medium: 8 vCPUs/32GB RAM, large: 16 vCPUs/64GB RAM)"
  type        = string
  default     = "medium"

  validation {
    condition     = contains(["medium", "large"], var.ce_site_size)
    error_message = "CE site size must be 'medium' or 'large'. Reference: https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/reference/ce-site-size-ref"
  }
}

variable "ssh_public_key" {
  description = "SSH public key for CE VM access (optional - will be auto-generated if not provided)"
  type        = string
  default     = ""
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    environment = "dev"
    managed_by  = "terraform"
    project     = "f5-xc-ce-azure"
  }
}

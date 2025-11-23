# Variables for Azure Hub VNET Module
# Updated for 3-NIC CE Architecture: Management, External, Internal subnets

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "vnet_name" {
  description = "Name of the hub virtual network"
  type        = string
}

variable "address_space" {
  description = "Address space for the hub VNET"
  type        = list(string)
}

# Management Subnet - For RE tunnel, SSH access, F5 XC console communication
variable "mgmt_subnet_name" {
  description = "Name of the management subnet (Azure CAF: snet-hub-management)"
  type        = string
  default     = "snet-hub-management"
}

variable "mgmt_subnet_prefix" {
  description = "Address prefix for management subnet"
  type        = string
}

# External Subnet - For External Load Balancer backend (public traffic)
variable "external_subnet_name" {
  description = "Name of the external subnet (Azure CAF: snet-hub-external)"
  type        = string
  default     = "snet-hub-external"
}

variable "external_subnet_prefix" {
  description = "Address prefix for external subnet (minimum /26)"
  type        = string
}

# Internal Subnet - For Internal Load Balancer backend (spoke routing)
variable "internal_subnet_name" {
  description = "Name of the internal subnet (Azure CAF: snet-hub-internal)"
  type        = string
  default     = "snet-hub-internal"
}

variable "internal_subnet_prefix" {
  description = "Address prefix for internal subnet (minimum /26)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

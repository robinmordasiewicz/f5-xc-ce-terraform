# Variables for Azure Hub VNET Module

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

variable "nva_subnet_name" {
  description = "Name of the NVA subnet"
  type        = string
  default     = "nva-subnet"
}

variable "nva_subnet_prefix" {
  description = "Address prefix for NVA subnet (minimum /26)"
  type        = string
}

variable "mgmt_subnet_name" {
  description = "Name of the management subnet"
  type        = string
  default     = "management-subnet"
}

variable "mgmt_subnet_prefix" {
  description = "Address prefix for management subnet"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

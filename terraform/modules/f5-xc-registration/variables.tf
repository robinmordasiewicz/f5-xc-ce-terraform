# Variables for F5 XC Registration Module

variable "site_name" {
  description = "Name of the CE site"
  type        = string
}

variable "namespace" {
  description = "F5 XC namespace"
  type        = string
  default     = "system"
}

variable "azure_region" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
}

variable "vnet_name" {
  description = "VNET name"
  type        = string
}

variable "subnet_name" {
  description = "Subnet name for CE"
  type        = string
}

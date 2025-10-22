# Variables for Azure Spoke VNET Module

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "vnet_name" {
  description = "Name of the spoke virtual network"
  type        = string
}

variable "address_space" {
  description = "Address space for the spoke VNET"
  type        = list(string)
}

variable "workload_subnet_prefix" {
  description = "Address prefix for workload subnet"
  type        = string
}

variable "hub_vnet_id" {
  description = "ID of the hub VNET for peering"
  type        = string
}

variable "hub_nva_ip" {
  description = "IP address of hub NVA for routing"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Variables for F5 XC CE Managed Kubernetes Module

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "vm_name" {
  description = "Name of the CE K8s VM"
  type        = string
}

variable "vm_size" {
  description = "Size of the CE VM"
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

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

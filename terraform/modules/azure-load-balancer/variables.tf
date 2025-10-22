# Variables for Azure Load Balancer Module

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "lb_name" {
  description = "Name of the load balancer"
  type        = string
}

variable "subnet_id" {
  description = "ID of the subnet for frontend IP"
  type        = string
}

variable "frontend_ip_address" {
  description = "Static IP address for load balancer frontend"
  type        = string
}

variable "backend_pool_name" {
  description = "Name of the backend pool"
  type        = string
  default     = "ce-backend-pool"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Variables for Azure External Load Balancer Module

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "lb_name" {
  description = "Name of the external load balancer"
  type        = string
}

variable "availability_zones" {
  description = "Availability zones for the public IP (zone-redundant)"
  type        = list(string)
  default     = ["1", "2", "3"]
}

variable "health_probe_port" {
  description = "Port for TCP health probe"
  type        = number
  default     = 80
}

variable "health_probe_interval" {
  description = "Interval in seconds between health probes"
  type        = number
  default     = 5
}

variable "health_probe_threshold" {
  description = "Number of consecutive probe failures before marking unhealthy"
  type        = number
  default     = 2
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

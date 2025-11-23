# Azure External Load Balancer Module
#
# Creates a public-facing Azure Load Balancer for F5 XC CE instances.
# Routes external traffic (DNS, HTTP, HTTPS, high ports) to CE external NICs.
#
# Resources Created:
# - Public IP address for load balancer frontend
# - Standard SKU Load Balancer
# - Backend address pool for CE external NICs
# - Health probes (TCP and HTTPS)
# - Load balancer rules for DNS, HTTP, HTTPS, and high ports

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.54"
    }
  }
}

# Public IP for External Load Balancer
resource "azurerm_public_ip" "external_lb" {
  name                = "${var.lb_name}-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = var.availability_zones

  tags = var.tags
}

# External Load Balancer
resource "azurerm_lb" "external" {
  name                = var.lb_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"

  frontend_ip_configuration {
    name                 = "external-frontend"
    public_ip_address_id = azurerm_public_ip.external_lb.id
  }

  tags = var.tags
}

# Backend Address Pool for CE External NICs
resource "azurerm_lb_backend_address_pool" "external" {
  loadbalancer_id = azurerm_lb.external.id
  name            = "ce-external-backend-pool"
}

# ============================================================================
# HEALTH PROBES
# ============================================================================

# TCP Health Probe (primary)
resource "azurerm_lb_probe" "tcp" {
  loadbalancer_id     = azurerm_lb.external.id
  name                = "tcp-health-probe"
  port                = var.health_probe_port
  protocol            = "Tcp"
  interval_in_seconds = var.health_probe_interval
  number_of_probes    = var.health_probe_threshold
}

# HTTPS Health Probe (secondary)
resource "azurerm_lb_probe" "https" {
  loadbalancer_id     = azurerm_lb.external.id
  name                = "https-health-probe"
  port                = 443
  protocol            = "Tcp"
  interval_in_seconds = var.health_probe_interval
  number_of_probes    = var.health_probe_threshold
}

# ============================================================================
# LOAD BALANCER RULES
# ============================================================================

# DNS TCP (port 53)
resource "azurerm_lb_rule" "dns_tcp" {
  loadbalancer_id                = azurerm_lb.external.id
  name                           = "DNS-TCP"
  protocol                       = "Tcp"
  frontend_port                  = 53
  backend_port                   = 53
  frontend_ip_configuration_name = "external-frontend"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.external.id]
  probe_id                       = azurerm_lb_probe.tcp.id
  enable_floating_ip             = false
  idle_timeout_in_minutes        = 4
  load_distribution              = "Default"
}

# DNS UDP (port 53)
resource "azurerm_lb_rule" "dns_udp" {
  loadbalancer_id                = azurerm_lb.external.id
  name                           = "DNS-UDP"
  protocol                       = "Udp"
  frontend_port                  = 53
  backend_port                   = 53
  frontend_ip_configuration_name = "external-frontend"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.external.id]
  probe_id                       = azurerm_lb_probe.tcp.id
  enable_floating_ip             = false
  idle_timeout_in_minutes        = 4
  load_distribution              = "Default"
}

# HTTP (port 80)
resource "azurerm_lb_rule" "http" {
  loadbalancer_id                = azurerm_lb.external.id
  name                           = "HTTP"
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "external-frontend"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.external.id]
  probe_id                       = azurerm_lb_probe.tcp.id
  enable_floating_ip             = false
  idle_timeout_in_minutes        = 4
  load_distribution              = "Default"
}

# HTTPS (port 443)
resource "azurerm_lb_rule" "https" {
  loadbalancer_id                = azurerm_lb.external.id
  name                           = "HTTPS"
  protocol                       = "Tcp"
  frontend_port                  = 443
  backend_port                   = 443
  frontend_ip_configuration_name = "external-frontend"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.external.id]
  probe_id                       = azurerm_lb_probe.https.id
  enable_floating_ip             = false
  idle_timeout_in_minutes        = 4
  load_distribution              = "Default"
}

# Note: HA Ports (port 0) rules are NOT permitted on public load balancers in Azure.
# Public LBs must use specific port rules only (DNS, HTTP, HTTPS configured above).
# For high-port traffic (1024-65535), use Internal LB with HA Ports or configure
# specific port ranges as individual rules if needed.

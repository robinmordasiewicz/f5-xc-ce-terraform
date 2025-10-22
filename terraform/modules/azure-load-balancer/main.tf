# Azure Load Balancer Module
#
# Internal load balancer for F5 XC CE NVA high availability (active/active).
# Provides HA for CE AppStack instances with health probes and load balancing rules.
#
# Resources Created:
# - Internal load balancer
# - Backend address pool
# - Health probes (TCP 65500, HTTPS 65443)
# - Load balancing rules
# - HA ports rule (all protocols, all ports)

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

# T041: Internal Load Balancer
resource "azurerm_lb" "internal" {
  name                = var.lb_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard" # Standard SKU required for HA ports

  frontend_ip_configuration {
    name                          = "LoadBalancerFrontEnd"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.frontend_ip_address
  }

  tags = var.tags
}

# T042: Backend Address Pool
resource "azurerm_lb_backend_address_pool" "ce_pool" {
  loadbalancer_id = azurerm_lb.internal.id
  name            = var.backend_pool_name
}

# T043: Health Probe - TCP 65500 (CE control plane health check)
resource "azurerm_lb_probe" "ce_tcp" {
  loadbalancer_id     = azurerm_lb.internal.id
  name                = "ce-health-probe-tcp"
  protocol            = "Tcp"
  port                = 65500
  interval_in_seconds = 5
  number_of_probes    = 2
}

# Health Probe - HTTPS 65443 (CE HTTPS health check)
resource "azurerm_lb_probe" "ce_https" {
  loadbalancer_id     = azurerm_lb.internal.id
  name                = "ce-health-probe-https"
  protocol            = "Https"
  port                = 65443
  request_path        = "/"
  interval_in_seconds = 5
  number_of_probes    = 2
}

# T044: Load Balancing Rule for HTTPS (443)
resource "azurerm_lb_rule" "https" {
  loadbalancer_id                = azurerm_lb.internal.id
  name                           = "LBRuleHTTPS"
  protocol                       = "Tcp"
  frontend_port                  = 443
  backend_port                   = 443
  frontend_ip_configuration_name = "LoadBalancerFrontEnd"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.ce_pool.id]
  probe_id                       = azurerm_lb_probe.ce_tcp.id
  enable_floating_ip             = false
  idle_timeout_in_minutes        = 4
  load_distribution              = "SourceIPProtocol" # Session affinity
}

# Load Balancing Rule for HTTP (80)
resource "azurerm_lb_rule" "http" {
  loadbalancer_id                = azurerm_lb.internal.id
  name                           = "LBRuleHTTP"
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "LoadBalancerFrontEnd"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.ce_pool.id]
  probe_id                       = azurerm_lb_probe.ce_tcp.id
  enable_floating_ip             = false
  idle_timeout_in_minutes        = 4
  load_distribution              = "SourceIPProtocol"
}

# T045: HA Ports Rule (all protocols, all ports)
# This enables all traffic to flow through the CE NVAs for full NVA functionality
resource "azurerm_lb_rule" "ha_ports" {
  loadbalancer_id                = azurerm_lb.internal.id
  name                           = "HAPortsRule"
  protocol                       = "All"
  frontend_port                  = 0 # All ports
  backend_port                   = 0 # All ports
  frontend_ip_configuration_name = "LoadBalancerFrontEnd"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.ce_pool.id]
  probe_id                       = azurerm_lb_probe.ce_tcp.id
  enable_floating_ip             = true # Required for HA ports
  idle_timeout_in_minutes        = 4
}

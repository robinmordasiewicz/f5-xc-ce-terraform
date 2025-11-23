# Azure Internal Load Balancer Module
#
# Internal load balancer for F5 XC CE NVA high availability (active/active).
# Routes spoke VNET traffic to CE internal NICs for NVA routing.
#
# Resources Created:
# - Internal Standard SKU load balancer
# - Backend address pool for CE internal NICs
# - Health probes (TCP)
# - HA Ports rule (all ports/protocols for NVA routing)

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.54"
    }
  }
}

# Internal Load Balancer for spoke routing
resource "azurerm_lb" "internal" {
  name                = var.lb_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard" # Standard SKU required for HA ports

  frontend_ip_configuration {
    name                          = "internal-frontend"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.frontend_ip_address
  }

  tags = var.tags
}

# Backend Address Pool for CE Internal NICs
resource "azurerm_lb_backend_address_pool" "internal" {
  loadbalancer_id = azurerm_lb.internal.id
  name            = "ce-internal-backend-pool"
}

# Health Probe - TCP (for HA ports)
resource "azurerm_lb_probe" "tcp" {
  loadbalancer_id     = azurerm_lb.internal.id
  name                = "internal-health-probe-tcp"
  protocol            = "Tcp"
  port                = var.health_probe_port
  interval_in_seconds = var.health_probe_interval
  number_of_probes    = var.health_probe_threshold
}

# HA Ports Rule - All protocols, all ports (required for NVA routing)
# This allows the internal LB to route ANY traffic from spoke VNETs through the CEs
resource "azurerm_lb_rule" "ha_ports" {
  loadbalancer_id                = azurerm_lb.internal.id
  name                           = "HAPortsRule"
  protocol                       = "All"
  frontend_port                  = 0 # HA Ports - all ports
  backend_port                   = 0 # HA Ports - all ports
  frontend_ip_configuration_name = "internal-frontend"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.internal.id]
  probe_id                       = azurerm_lb_probe.tcp.id
  enable_floating_ip             = true # Required for NVA/transparent proxy scenarios
  idle_timeout_in_minutes        = 4
  load_distribution              = "SourceIPProtocol" # Session affinity for stateful flows
}

# Azure Spoke VNET Module
#
# Creates spoke virtual network with VNET peering to hub and User Defined Routes (UDR)
# to route traffic through hub NVA (F5 XC CE AppStack).
#
# Resources Created:
# - Spoke virtual network
# - Workload subnet
# - VNET peering (hub ↔ spoke)
# - Network Security Group
# - Route table with default route to hub NVA

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

# Extract hub VNET name from hub VNET ID for peering
locals {
  hub_vnet_name           = split("/", var.hub_vnet_id)[8]
  hub_resource_group_name = split("/", var.hub_vnet_id)[4]
}

# T036: Spoke Virtual Network
resource "azurerm_virtual_network" "spoke" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space

  tags = var.tags
}

# T037: Workload Subnet
resource "azurerm_subnet" "workload" {
  name                 = "workload-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.spoke.name
  address_prefixes     = [var.workload_subnet_prefix]
}

# T038: VNET Peering (Spoke to Hub)
resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "${var.vnet_name}-to-hub"
  resource_group_name       = var.resource_group_name
  virtual_network_name      = azurerm_virtual_network.spoke.name
  remote_virtual_network_id = var.hub_vnet_id

  allow_virtual_network_access = true
  allow_forwarded_traffic      = true # Allow forwarded traffic from hub NVA
  allow_gateway_transit        = false
  use_remote_gateways          = false
}

# VNET Peering (Hub to Spoke) - requires hub resource group
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  name                      = "hub-to-${var.vnet_name}"
  resource_group_name       = local.hub_resource_group_name
  virtual_network_name      = local.hub_vnet_name
  remote_virtual_network_id = azurerm_virtual_network.spoke.id

  allow_virtual_network_access = true
  allow_forwarded_traffic      = true # Allow traffic to be forwarded to spoke
  allow_gateway_transit        = false
  use_remote_gateways          = false
}

# T039: Network Security Group for Workload Subnet
resource "azurerm_network_security_group" "workload" {
  name                = "${var.vnet_name}-workload-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Allow traffic from hub VNET
  security_rule {
    name                       = "AllowHubTraffic"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  # Allow outbound traffic to hub NVA
  security_rule {
    name                       = "AllowOutboundToHub"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "10.0.0.0/8"
  }

  # Allow outbound to internet (will route through hub NVA via UDR)
  security_rule {
    name                       = "AllowOutboundInternet"
    priority                   = 110
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  tags = var.tags
}

# Associate NSG with workload subnet
resource "azurerm_subnet_network_security_group_association" "workload" {
  subnet_id                 = azurerm_subnet.workload.id
  network_security_group_id = azurerm_network_security_group.workload.id
}

# T040: Route Table with UDR to Hub NVA
resource "azurerm_route_table" "spoke" {
  name                          = "${var.vnet_name}-rt"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  disable_bgp_route_propagation = true # Disable BGP propagation for UDR

  # Default route to hub NVA (0.0.0.0/0 → hub NVA IP)
  route {
    name                   = "DefaultRouteToHubNVA"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = var.hub_nva_ip
  }

  # Route RFC 1918 private addresses to hub NVA
  route {
    name                   = "RFC1918-10-ToHubNVA"
    address_prefix         = "10.0.0.0/8"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = var.hub_nva_ip
  }

  route {
    name                   = "RFC1918-172-ToHubNVA"
    address_prefix         = "172.16.0.0/12"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = var.hub_nva_ip
  }

  route {
    name                   = "RFC1918-192-ToHubNVA"
    address_prefix         = "192.168.0.0/16"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = var.hub_nva_ip
  }

  tags = var.tags
}

# Associate route table with workload subnet
resource "azurerm_subnet_route_table_association" "workload" {
  subnet_id      = azurerm_subnet.workload.id
  route_table_id = azurerm_route_table.spoke.id
}

# Azure Hub VNET Module
#
# Creates hub virtual network with subnets for Network Virtual Appliance (NVA)
# deployment. The hub VNET centralizes connectivity and hosts CE AppStack instances.
#
# Resources Created:
# - Virtual network (hub)
# - NVA subnet (for CE AppStack instances)
# - Management subnet (for operational access)
# - Network Security Groups
# - Route tables

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

# T031: Hub Virtual Network
resource "azurerm_virtual_network" "hub" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space

  tags = var.tags
}

# T032: NVA Subnet (for CE AppStack instances)
resource "azurerm_subnet" "nva" {
  name                 = var.nva_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.nva_subnet_prefix]

  # Disable private endpoint network policies for NVA subnet
  private_endpoint_network_policies_enabled = false
}

# T033: Management Subnet
resource "azurerm_subnet" "mgmt" {
  name                 = var.mgmt_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.mgmt_subnet_prefix]
}

# T034: Network Security Group for NVA Subnet
resource "azurerm_network_security_group" "nva" {
  name                = "${var.vnet_name}-nva-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Allow F5 XC control plane (HTTPS 443)
  security_rule {
    name                       = "AllowF5XCControlPlane"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  # Allow CE health probe (TCP 65500)
  security_rule {
    name                       = "AllowCEHealthProbe"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "65500"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  # Allow HTTPS health probe (TCP 65443)
  security_rule {
    name                       = "AllowCEHTTPSHealthProbe"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "65443"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  # Allow traffic from spoke VNETs (all protocols for NVA functionality)
  security_rule {
    name                       = "AllowSpokeTraffic"
    priority                   = 130
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

# Associate NSG with NVA subnet
resource "azurerm_subnet_network_security_group_association" "nva" {
  subnet_id                 = azurerm_subnet.nva.id
  network_security_group_id = azurerm_network_security_group.nva.id
}

# Network Security Group for Management Subnet
resource "azurerm_network_security_group" "mgmt" {
  name                = "${var.vnet_name}-mgmt-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Allow SSH from Azure Bastion subnet (if used)
  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  # Allow HTTPS management
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

# Associate NSG with management subnet
resource "azurerm_subnet_network_security_group_association" "mgmt" {
  subnet_id                 = azurerm_subnet.mgmt.id
  network_security_group_id = azurerm_network_security_group.mgmt.id
}

# T035: Route Table for Hub (default route to internet)
resource "azurerm_route_table" "hub" {
  name                          = "${var.vnet_name}-rt"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  disable_bgp_route_propagation = false

  # Default route to internet (CE provides internet connectivity)
  route {
    name           = "DefaultRouteToInternet"
    address_prefix = "0.0.0.0/0"
    next_hop_type  = "Internet"
  }

  tags = var.tags
}

# Associate route table with NVA subnet
resource "azurerm_subnet_route_table_association" "nva" {
  subnet_id      = azurerm_subnet.nva.id
  route_table_id = azurerm_route_table.hub.id
}

# Azure Hub VNET Module
#
# Creates hub virtual network with 3 subnets for 3-NIC CE deployment:
# - Management Subnet: RE tunnel, SSH access, F5 XC console communication
# - External Subnet: External Load Balancer backend (public traffic)
# - Internal Subnet: Internal Load Balancer backend (spoke routing)
#
# Resources Created:
# - Virtual network (hub)
# - Management subnet (for CE management NICs with public IPs)
# - External subnet (for CE external NICs, External LB backend)
# - Internal subnet (for CE internal NICs, Internal LB backend)
# - Network Security Groups for each subnet
# - Route tables

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.54"
    }
  }
}

# Hub Virtual Network
resource "azurerm_virtual_network" "hub" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space

  tags = var.tags
}

# ============================================================================
# MANAGEMENT SUBNET - For RE tunnel, SSH, F5 XC console (with Public IPs)
# ============================================================================

resource "azurerm_subnet" "mgmt" {
  name                 = var.mgmt_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.mgmt_subnet_prefix]
}

resource "azurerm_network_security_group" "mgmt" {
  name                = "${var.vnet_name}-mgmt-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Allow SSH from anywhere (management access via public IP)
  security_rule {
    name                       = "AllowSSHInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow F5 XC control plane outbound (HTTPS 443 to ves.volterra.io)
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

  # Allow RE tunnel communication (various ports to F5 XC infrastructure)
  security_rule {
    name                       = "AllowF5XCTunnel"
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

resource "azurerm_subnet_network_security_group_association" "mgmt" {
  subnet_id                 = azurerm_subnet.mgmt.id
  network_security_group_id = azurerm_network_security_group.mgmt.id
}

# ============================================================================
# EXTERNAL SUBNET - For External Load Balancer backend (public traffic)
# ============================================================================

resource "azurerm_subnet" "external" {
  name                 = var.external_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.external_subnet_prefix]

  # Disable private endpoint network policies
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_network_security_group" "external" {
  name                = "${var.vnet_name}-external-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Allow DNS (TCP/UDP 53) from External LB
  security_rule {
    name                       = "AllowDNSTCP"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "53"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowDNSUDP"
    priority                   = 101
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Udp"
    source_port_range          = "*"
    destination_port_range     = "53"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow HTTP (80)
  security_rule {
    name                       = "AllowHTTP"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow HTTPS (443)
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow non-privileged ports (>1024)
  security_rule {
    name                       = "AllowHighPorts"
    priority                   = 130
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "1024-65535"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow Azure Load Balancer health probes
  security_rule {
    name                       = "AllowAzureLBProbes"
    priority                   = 140
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "external" {
  subnet_id                 = azurerm_subnet.external.id
  network_security_group_id = azurerm_network_security_group.external.id
}

# ============================================================================
# INTERNAL SUBNET - For Internal Load Balancer backend (spoke routing)
# ============================================================================

resource "azurerm_subnet" "internal" {
  name                 = var.internal_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.internal_subnet_prefix]

  # Disable private endpoint network policies
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_network_security_group" "internal" {
  name                = "${var.vnet_name}-internal-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Allow all traffic from spoke VNETs (10.0.0.0/8)
  security_rule {
    name                       = "AllowSpokeTraffic"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }

  # Allow Azure Load Balancer health probes
  security_rule {
    name                       = "AllowAzureLBProbes"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  # Allow all outbound (for routing to spoke workloads)
  security_rule {
    name                       = "AllowAllOutbound"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "internal" {
  subnet_id                 = azurerm_subnet.internal.id
  network_security_group_id = azurerm_network_security_group.internal.id
}

# ============================================================================
# ROUTE TABLES
# ============================================================================

# Route table for hub (default route to internet for management)
resource "azurerm_route_table" "hub" {
  name                          = "${var.vnet_name}-rt"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  bgp_route_propagation_enabled = true

  # Default route to internet (CE provides internet connectivity)
  route {
    name           = "DefaultRouteToInternet"
    address_prefix = "0.0.0.0/0"
    next_hop_type  = "Internet"
  }

  tags = var.tags
}

# Associate route table with management subnet
resource "azurerm_subnet_route_table_association" "mgmt" {
  subnet_id      = azurerm_subnet.mgmt.id
  route_table_id = azurerm_route_table.hub.id
}

# Associate route table with external subnet
resource "azurerm_subnet_route_table_association" "external" {
  subnet_id      = azurerm_subnet.external.id
  route_table_id = azurerm_route_table.hub.id
}

# F5 XC CE AppStack Module (3-NIC Architecture)
#
# Deploys F5 XC Customer Edge (CE) AppStack instance as Network Virtual Appliance (NVA)
# in hub VNET with 3 NICs for management, external, and internal traffic separation.
#
# NIC Configuration:
# - Management NIC: RE tunnel, SSH, F5 XC Console (with public IP) - Primary NIC
# - External NIC: External LB backend pool for inbound public traffic
# - Internal NIC: Internal LB backend pool for spoke VNET routing
#
# Resources Created:
# - Public IP for management access
# - 3 Network Interfaces with IP forwarding enabled
# - Virtual Machine with F5 XC CE Ubuntu image
# - Cloud-init configuration with registration token
# - Managed identity for Azure integration
# - Load balancer backend pool associations
# - Boot diagnostics for troubleshooting
#
# Prerequisites:
# - F5 XC registration token from registration module
# - External and Internal load balancer backend pools created
# - Management, External, and Internal subnets exist

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.54"
    }
  }
}

# Public IP for Management Access
resource "azurerm_public_ip" "ce_mgmt" {
  name                = "${var.vm_name}-mgmt-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = [var.availability_zone]

  tags = var.tags
}

# Managed Identity for CE VM
resource "azurerm_user_assigned_identity" "ce" {
  name                = "${var.vm_name}-identity"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# Management NIC - RE tunnel, SSH, F5 XC Console (Primary NIC with Public IP)
resource "azurerm_network_interface" "ce_mgmt" {
  name                           = "${var.vm_name}-mgmt-nic"
  location                       = var.location
  resource_group_name            = var.resource_group_name
  ip_forwarding_enabled          = true # Required for NVA functionality
  accelerated_networking_enabled = var.enable_accelerated_networking

  ip_configuration {
    name                          = "mgmt"
    subnet_id                     = var.mgmt_subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.ce_mgmt.id
    primary                       = true
  }

  tags = var.tags
}

# External NIC - External LB backend (Public traffic ingress)
resource "azurerm_network_interface" "ce_external" {
  name                           = "${var.vm_name}-external-nic"
  location                       = var.location
  resource_group_name            = var.resource_group_name
  ip_forwarding_enabled          = true # Required for NVA functionality
  accelerated_networking_enabled = var.enable_accelerated_networking

  ip_configuration {
    name                          = "external"
    subnet_id                     = var.external_subnet_id
    private_ip_address_allocation = "Dynamic"
  }

  tags = var.tags
}

# Internal NIC - Internal LB backend (Spoke VNET routing)
resource "azurerm_network_interface" "ce_internal" {
  name                           = "${var.vm_name}-internal-nic"
  location                       = var.location
  resource_group_name            = var.resource_group_name
  ip_forwarding_enabled          = true # Required for NVA functionality
  accelerated_networking_enabled = var.enable_accelerated_networking

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.internal_subnet_id
    private_ip_address_allocation = "Dynamic"
  }

  tags = var.tags
}

# Associate External NIC with External Load Balancer Backend Pool
resource "azurerm_network_interface_backend_address_pool_association" "ce_external" {
  network_interface_id    = azurerm_network_interface.ce_external.id
  ip_configuration_name   = "external"
  backend_address_pool_id = var.external_lb_backend_pool_id
}

# Associate Internal NIC with Internal Load Balancer Backend Pool
resource "azurerm_network_interface_backend_address_pool_association" "ce_internal" {
  network_interface_id    = azurerm_network_interface.ce_internal.id
  ip_configuration_name   = "internal"
  backend_address_pool_id = var.internal_lb_backend_pool_id
}

# Cloud-init Configuration with Registration Token
# Per F5 DevCentral best practices, cloud-init writes directly to /etc/vpm/config.yaml
# with full VPM configuration including CertifiedHardwareEndpoint for Azure
data "cloudinit_config" "ce_config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content = yamlencode({
      write_files = [
        {
          path        = "/etc/hosts"
          permissions = "0644"
          owner       = "root:root"
          content     = "127.0.0.1 localhost\n127.0.0.1 vip\n"
        },
        {
          path        = "/etc/vpm/config.yaml"
          permissions = "0644"
          owner       = "root:root"
          content = yamlencode({
            Vpm = {
              ClusterType               = "ce"
              ClusterName               = var.site_name
              Token                     = var.registration_token
              MauricePrivateEndpoint    = "https://register-tls.ves.volterra.io"
              MauriceEndpoint           = "https://register.ves.volterra.io"
              CertifiedHardwareEndpoint = "https://vesio.blob.core.windows.net/releases/certified-hardware/azure.yml"
              Latitude                  = 0.0
              Longitude                 = 0.0
            }
            Kubernetes = {
              EtcdUseTLS    = true
              Server        = "vip"
              CloudProvider = "disabled"
            }
          })
        }
      ]
    })
  }
}

# CE Virtual Machine with 3 NICs
resource "azurerm_linux_virtual_machine" "ce" {
  name                = var.vm_name
  location            = var.location
  resource_group_name = var.resource_group_name
  size                = var.vm_size # Standard_D8s_v3 (8 vCPUs, 32 GB RAM)
  zone                = var.availability_zone

  # Admin configuration
  admin_username                  = var.admin_username
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  # Network interfaces - Management NIC MUST be first (primary)
  # Order matters: Azure uses first NIC as primary
  network_interface_ids = [
    azurerm_network_interface.ce_mgmt.id,     # Primary - Management
    azurerm_network_interface.ce_external.id, # Secondary - External LB
    azurerm_network_interface.ce_internal.id, # Tertiary - Internal LB
  ]

  # F5 XC CE Ubuntu Image
  source_image_reference {
    publisher = "volterraedgeservices"
    offer     = "volterra-node"
    sku       = "volterra-node"
    version   = "latest"
  }

  plan {
    name      = "volterra-node"
    product   = "volterra-node"
    publisher = "volterraedgeservices"
  }

  # OS Disk Configuration
  os_disk {
    name                 = "${var.vm_name}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS" # Standard SSD per F5 XC documentation
    disk_size_gb         = 80
  }

  # Cloud-init with registration token
  custom_data = data.cloudinit_config.ce_config.rendered

  # Managed Identity
  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.ce.id
    ]
  }

  # Boot Diagnostics
  boot_diagnostics {
    storage_account_uri = null # Use managed storage account
  }

  # Tags and Metadata
  tags = merge(
    var.tags,
    {
      role        = "f5-xc-ce-appstack"
      nva_type    = "secure-mesh-site"
      environment = "production"
    }
  )

  lifecycle {
    ignore_changes = [
      # Ignore changes to custom_data after initial creation
      custom_data,
    ]
  }
}

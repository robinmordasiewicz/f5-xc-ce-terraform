# F5 XC CE AppStack Module
#
# Deploys F5 XC Customer Edge (CE) AppStack instance as Network Virtual Appliance (NVA)
# in hub VNET. CE provides secure connectivity, traffic inspection, and application services.
#
# Resources Created:
# - Public IP (for management access and F5 XC Console communication)
# - Network Interface with IP forwarding enabled
# - Virtual Machine with F5 XC CE Ubuntu image
# - Cloud-init configuration with registration token
# - Managed identity for Azure integration
# - Load balancer backend pool association
# - Boot diagnostics for troubleshooting
#
# Prerequisites:
# - F5 XC registration token from registration module
# - Load balancer backend pool created
# - Subnet for CE deployment exists

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

# T053: Public IP for Management Access
resource "azurerm_public_ip" "ce_mgmt" {
  name                = "${var.vm_name}-mgmt-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = [var.availability_zone]

  tags = var.tags
}

# T058: Managed Identity for CE VM
resource "azurerm_user_assigned_identity" "ce" {
  name                = "${var.vm_name}-identity"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# T052: Network Interface with IP Forwarding
resource "azurerm_network_interface" "ce" {
  name                           = "${var.vm_name}-nic"
  location                       = var.location
  resource_group_name            = var.resource_group_name
  ip_forwarding_enabled          = true # Required for NVA functionality
  accelerated_networking_enabled = var.enable_accelerated_networking

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.ce_mgmt.id
  }

  tags = var.tags
}

# T061: Associate NIC with Load Balancer Backend Pool
resource "azurerm_network_interface_backend_address_pool_association" "ce" {
  network_interface_id    = azurerm_network_interface.ce.id
  ip_configuration_name   = "internal"
  backend_address_pool_id = var.lb_backend_pool_id
}

# T056: Cloud-init Configuration with Registration Token
data "cloudinit_config" "ce_config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content = yamlencode({
      write_files = [
        {
          path        = "/etc/vpm/user_data"
          permissions = "0644"
          owner       = "root:root"
          encoding    = "b64"
          content = base64encode(jsonencode({
            token                 = var.registration_token
            cluster_name          = var.vm_name
            maurice_endpoint      = "https://register.ves.volterra.io/register"
            maurice_mtls_endpoint = "https://register-tls.ves.volterra.io/register"
            latitude              = 0.0
            longitude             = 0.0
          }))
        }
      ]
    })
  }
}

# T051, T054, T055, T057, T059, T060, T063: CE Virtual Machine
resource "azurerm_linux_virtual_machine" "ce" {
  name                = var.vm_name
  location            = var.location
  resource_group_name = var.resource_group_name
  size                = var.vm_size           # T057: Standard_D8s_v3 (8 vCPUs, 32 GB RAM)
  zone                = var.availability_zone # T060

  # Admin configuration
  admin_username                  = var.admin_username
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  # Network interface
  network_interface_ids = [
    azurerm_network_interface.ce.id,
  ]

  # T055: F5 XC CE Ubuntu Image
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

  # T054: OS Disk Configuration
  os_disk {
    name                 = "${var.vm_name}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS" # Standard SSD per F5 XC documentation
    disk_size_gb         = 80
  }

  # T056: Cloud-init with registration token
  custom_data = data.cloudinit_config.ce_config.rendered

  # T058: Managed Identity
  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.ce.id
    ]
  }

  # T059: Boot Diagnostics
  boot_diagnostics {
    storage_account_uri = null # Use managed storage account
  }

  # T063: Tags and Metadata
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

# F5 XC Registration Module
#
# Creates F5 XC CE site and generates registration token for CE AppStack instances.
# The registration token is used by CE VMs to authenticate with F5 XC Console during boot.
#
# Resources Created:
# - Azure VNET site in F5 XC Console
# - Registration token for CE instances
#
# Prerequisites:
# - F5 XC API token configured via provider
# - Azure VNET and subnet must exist

terraform {
  required_providers {
    volterra = {
      source  = "volterraedge/volterra"
      version = "~> 0.11"
    }
  }
}

# T047: Create Azure VNET Site in F5 XC Console
resource "volterra_azure_vnet_site" "ce_site" {
  name      = var.site_name
  namespace = var.namespace

  # Azure region
  azure_region = var.azure_region

  # Resource group
  resource_group = var.resource_group_name

  # Machine type (Standard_D8s_v3: 8 vCPUs, 32 GB RAM)
  machine_type = "Standard_D8s_v3"

  # Ingress/Egress Gateway configuration (Secure Mesh Site)
  ingress_egress_gw {
    azure_certified_hw = "azure-byol-multi-nic-voltmesh"

    # Inside network (hub VNET subnet for CE instances)
    inside_network {
      existing_network {
        resource_group = var.resource_group_name
        vnet_name      = var.vnet_name
        subnet {
          subnet_name = var.subnet_name
        }
      }
    }

    # Performance mode (High performance for production)
    performance_enhancement_mode {
      perf_mode_l7_enhanced = true
    }

    # No outside network (internal LB only)
    no_outside_network = true

    # No forward proxy
    no_forward_proxy = true

    # Global network configuration
    no_global_network       = false
    no_inside_static_routes = false
  }

  # Operating system version
  os {
    default_os_version = true
  }

  # Site labels
  labels = {
    environment = "production"
    deployment  = "terraform"
  }

  # Lifecycle configuration
  lifecycle {
    ignore_changes = [
      # Ignore changes to labels managed by F5 XC Console
      labels,
    ]
  }
}

# T048: Generate Site Token
# Wait for site to be created, then get registration token
resource "volterra_site_state" "ce_site_state" {
  name           = volterra_azure_vnet_site.ce_site.name
  namespace      = var.namespace
  state          = "ONLINE" # Wait for site to be ONLINE
  wait_time      = 300      # Wait up to 5 minutes
  retry_interval = 10       # Check every 10 seconds
}

# T049: Extract Registration Token
# The token is available after site creation
data "volterra_registration_token" "ce_token" {
  name      = volterra_azure_vnet_site.ce_site.name
  namespace = var.namespace

  depends_on = [volterra_azure_vnet_site.ce_site]
}

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

# T047: Create Azure Secure Mesh Site (v2) in F5 XC Console
# Using volterra_securemesh_site_v2 for improved functionality and future-proof deployment
resource "volterra_securemesh_site_v2" "ce_site" {
  name      = var.site_name
  namespace = var.namespace

  # Site labels
  labels = {
    environment = "production"
    deployment  = "terraform"
  }

  # Azure provider configuration
  azure {
    not_managed {
      node_list {
        hostname = var.site_name

        # Configure interface for Site Local Inside (SLI) network
        interface_list {
          # Use existing Azure VNET subnet
          name        = "eth0"
          description = "Inside network interface for hub VNET connectivity"

          # Ethernet interface configuration
          ethernet_interface {
            device = "eth0"
          }

          # DHCP client for IP assignment
          dhcp_client = true

          # No IPv6 address
          no_ipv6_address = true

          # Network option: Site Local Inside (Local VRF)
          network_option {
            site_local_inside_network = true
          }

          # Enable site-to-site connectivity on this interface
          site_to_site_connectivity_interface_enabled = true

          # Interface priority
          priority = 1

          # Enable monitoring
          monitor_disabled = false
        }

        # Node type
        type = "Control"
      }
    }
  }

  # Performance enhancement mode (L7 optimized)
  performance_enhancement_mode {
    perf_mode_l7_enhanced = true
  }

  # Site Local Inside (SLI) local VRF configuration
  local_vrf {
    # Default SLI configuration
    default_sli_config = true

    # Default SLO (Site Local Outside) configuration
    default_config = true
  }

  # Disable forward proxy
  no_forward_proxy = true

  # Disable network policy (firewall)
  no_network_policy = true

  # Block all node local services (WebUI, SSH, DNS)
  block_all_services = true

  # Disable logs streaming
  logs_streaming_disabled = true

  # Enable High Availability
  enable_ha = true

  # Software settings - use defaults
  software_settings {
    os {
      default_os_version = true
    }
    sw {
      default_sw_version = true
    }
  }

  # Regional Edge (RE) selection - use geo proximity
  re_select {
    geo_proximity = true
  }

  # Disable site-to-site connectivity on SLI
  no_s2s_connectivity_sli = true

  # Disable site-to-site connectivity on SLO
  no_s2s_connectivity_slo = true

  # Offline survivability mode disabled
  offline_survivability_mode {
    no_offline_survivability_mode = true
  }

  # DNS and NTP configuration - use F5 defaults
  dns_ntp_config {
    f5_dns_default = true
    f5_ntp_default = true
  }

  # Lifecycle configuration
  lifecycle {
    ignore_changes = [
      # Ignore changes to labels managed by F5 XC Console
      labels,
    ]
  }
}

# T048: Create Site Registration Token
# Create a token for CE node registration with this site
resource "volterra_token" "ce_site_token" {
  name      = "${var.site_name}-token"
  namespace = var.namespace

  # Lifecycle: tokens are sensitive and should be rotated periodically
  lifecycle {
    create_before_destroy = true
  }
}

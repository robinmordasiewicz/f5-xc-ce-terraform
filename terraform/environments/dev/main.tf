# F5 XC CE Deployment to Azure - Development Environment
#
# This configuration deploys F5 XC Customer Edge (CE) mesh nodes to Azure
# with hub-and-spoke topology using 3-NIC architecture per CE.
#
# Architecture:
# - Hub VNET: 3 subnets (Management, External, Internal) hosting 2 CE VMs
# - Spoke VNET: Workload networks with User Defined Routes (UDR) to hub NVAs
# - External Load Balancer: Public IP with DNS, HTTP, HTTPS, high ports
# - Internal Load Balancer: HA Ports for spoke routing to CE internal NICs
# - Each CE operates as its own independent F5 XC site (cluster_size: 1)
#
# 3-NIC per CE Configuration:
# - Management NIC: RE tunnel, SSH, F5 XC console (with public IP)
# - External NIC: External LB backend pool (public ingress traffic)
# - Internal NIC: Internal LB backend pool (spoke VNET routing)
#
# Key Design:
# - Site 1: robinmordasiewicz-f5xc-azure-eastus-01 (VM1, AZ1)
# - Site 2: robinmordasiewicz-f5xc-azure-eastus-02 (VM2, AZ2)
# - Both sites are independent vsites load-balanced at Azure layer

# Azure Resource Group for Infrastructure
resource "azurerm_resource_group" "main" {
  name     = "${var.resource_group_name}-infra"
  location = var.azure_region

  tags = var.tags
}

# Auto-generate SSH key pair if not provided
resource "tls_private_key" "ce_ssh" {
  count     = var.ssh_public_key == "" ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Use provided SSH key or auto-generated one
locals {
  ssh_public_key = var.ssh_public_key != "" ? var.ssh_public_key : tls_private_key.ce_ssh[0].public_key_openssh

  # F5 XC CE site size to Azure VM SKU mapping
  ce_vm_size_map = {
    medium = "Standard_D8_v4"  # 8 vCPUs, 32 GB RAM
    large  = "Standard_D16_v4" # 16 vCPUs, 64 GB RAM
  }

  ce_vm_size = local.ce_vm_size_map[var.ce_site_size]

  # Identity information for F5 XC site labels and naming
  github_user = "robinmordasiewicz"
  github_repo = "f5-xc-ce-terraform"
  azure_user  = "r.mordasiewicz"

  # F5 XC site base naming - each CE gets its own unique site name
  f5xc_site_base = "${local.github_user}-f5xc-azure-${var.azure_region}"

  # Independent site names for each CE (NOT a cluster - separate vsites)
  f5xc_site_name_1 = "${local.f5xc_site_base}-01"
  f5xc_site_name_2 = "${local.f5xc_site_base}-02"

  # Comprehensive site labels for traceability
  site_labels_base = {
    owner             = local.azure_user
    github_user       = local.github_user
    github_repo       = local.github_repo
    repo_url          = "github.com-${local.github_user}-${local.github_repo}"
    environment       = var.tags["environment"]
    azure_region      = var.azure_region
    deployment_method = "terraform"
    managed_by        = "terraform"
  }

  # Site-specific labels
  site_labels_1 = merge(local.site_labels_base, {
    site_instance = "01"
    cluster_size  = "1"
  })

  site_labels_2 = merge(local.site_labels_base, {
    site_instance = "02"
    cluster_size  = "1"
  })
}

# ============================================================================
# NETWORKING: Hub VNET with 3 Subnets
# ============================================================================

# Hub VNET Module - 3 Subnet Architecture
module "hub_vnet" {
  source = "../../modules/azure-hub-vnet"

  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  vnet_name              = "hub-vnet"
  address_space          = var.hub_vnet_address_space
  mgmt_subnet_prefix     = var.hub_mgmt_subnet_prefix
  external_subnet_prefix = var.hub_external_subnet_prefix
  internal_subnet_prefix = var.hub_internal_subnet_prefix

  tags = var.tags
}

# Spoke VNET Module
module "spoke_vnet" {
  source = "../../modules/azure-spoke-vnet"

  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  vnet_name              = "${var.prefix}-spoke-vnet"
  address_space          = var.spoke_vnet_address_space
  workload_subnet_prefix = var.spoke_workload_subnet_prefix
  hub_vnet_id            = module.hub_vnet.vnet_id
  hub_nva_ip             = var.hub_nva_ip

  tags = var.tags

  depends_on = [module.hub_vnet]
}

# ============================================================================
# LOAD BALANCERS: External (Public) and Internal (Spoke Routing)
# ============================================================================

# External Load Balancer - Public IP for DNS, HTTP, HTTPS, High Ports
module "external_lb" {
  source = "../../modules/azure-external-lb"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  lb_name             = "lbe-${var.prefix}"

  tags = var.tags

  depends_on = [module.hub_vnet]
}

# Internal Load Balancer - HA Ports for Spoke Routing
module "internal_lb" {
  source = "../../modules/azure-load-balancer"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  lb_name             = "lbi-${var.prefix}"
  subnet_id           = module.hub_vnet.internal_subnet_id
  frontend_ip_address = var.internal_lb_frontend_ip

  tags = var.tags

  depends_on = [module.hub_vnet]
}

# ============================================================================
# SITE 1: Independent single-node F5 XC site
# ============================================================================

# F5 XC Registration for Site 1
module "f5_xc_registration_1" {
  source = "../../modules/f5-xc-registration"

  site_name           = local.f5xc_site_name_1 # robinmordasiewicz-f5xc-azure-eastus-01
  namespace           = var.f5_xc_namespace
  azure_region        = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  vnet_name           = module.hub_vnet.vnet_name
  subnet_name         = "snet-hub-external"
  site_labels         = local.site_labels_1

  depends_on = [module.hub_vnet]
}

# CE AppStack for Site 1 (3-NIC configuration)
module "ce_appstack_1" {
  source = "../../modules/f5-xc-ce-appstack"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vm_name             = "${var.prefix}-vm-01"
  site_name           = local.f5xc_site_name_1 # Unique site name for this CE
  vm_size             = local.ce_vm_size

  # 3-NIC subnet configuration
  mgmt_subnet_id     = module.hub_vnet.mgmt_subnet_id
  external_subnet_id = module.hub_vnet.external_subnet_id
  internal_subnet_id = module.hub_vnet.internal_subnet_id

  # Load balancer backend pools
  external_lb_backend_pool_id = module.external_lb.backend_pool_id
  internal_lb_backend_pool_id = module.internal_lb.backend_pool_id

  registration_token = module.f5_xc_registration_1.registration_token
  ssh_public_key     = local.ssh_public_key
  availability_zone  = "1"

  tags = merge(var.tags, { site_name = local.f5xc_site_name_1 })

  depends_on = [
    module.f5_xc_registration_1,
    module.external_lb,
    module.internal_lb
  ]
}

# ============================================================================
# SITE 2: Independent single-node F5 XC site
# ============================================================================

# F5 XC Registration for Site 2
module "f5_xc_registration_2" {
  source = "../../modules/f5-xc-registration"

  site_name           = local.f5xc_site_name_2 # robinmordasiewicz-f5xc-azure-eastus-02
  namespace           = var.f5_xc_namespace
  azure_region        = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  vnet_name           = module.hub_vnet.vnet_name
  subnet_name         = "snet-hub-external"
  site_labels         = local.site_labels_2

  depends_on = [module.hub_vnet]
}

# CE AppStack for Site 2 (3-NIC configuration)
module "ce_appstack_2" {
  source = "../../modules/f5-xc-ce-appstack"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vm_name             = "${var.prefix}-vm-02"
  site_name           = local.f5xc_site_name_2 # Unique site name for this CE
  vm_size             = local.ce_vm_size

  # 3-NIC subnet configuration
  mgmt_subnet_id     = module.hub_vnet.mgmt_subnet_id
  external_subnet_id = module.hub_vnet.external_subnet_id
  internal_subnet_id = module.hub_vnet.internal_subnet_id

  # Load balancer backend pools
  external_lb_backend_pool_id = module.external_lb.backend_pool_id
  internal_lb_backend_pool_id = module.internal_lb.backend_pool_id

  registration_token = module.f5_xc_registration_2.registration_token
  ssh_public_key     = local.ssh_public_key
  availability_zone  = "2"

  tags = merge(var.tags, { site_name = local.f5xc_site_name_2 })

  depends_on = [
    module.f5_xc_registration_2,
    module.external_lb,
    module.internal_lb
  ]
}

# ============================================================================
# AUTOMATIC REGISTRATION APPROVAL
# ============================================================================

# Automatic registration approval for Site 1 CE
# This resource waits for the CE VM to register and automatically approves it
resource "volterra_registration_approval" "site_1" {
  cluster_name = local.f5xc_site_name_1
  hostname     = module.ce_appstack_1.vm_name
  cluster_size = 1
  retry        = 10
  wait_time    = 60

  depends_on = [
    module.ce_appstack_1,
    module.f5_xc_registration_1
  ]
}

# Automatic registration approval for Site 2 CE
resource "volterra_registration_approval" "site_2" {
  cluster_name = local.f5xc_site_name_2
  hostname     = module.ce_appstack_2.vm_name
  cluster_size = 1
  retry        = 10
  wait_time    = 60

  depends_on = [
    module.ce_appstack_2,
    module.f5_xc_registration_2
  ]
}

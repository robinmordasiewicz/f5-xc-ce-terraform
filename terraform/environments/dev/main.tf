# F5 XC CE Deployment to Azure - Development Environment
#
# This configuration deploys a complete F5 XC Customer Edge (CE) environment to Azure
# with hub-and-spoke topology, load balancer HA, and automated registration.
#
# Architecture:
# - Hub VNET: Hosts CE AppStack instances as Network Virtual Appliances (NVAs)
# - Spoke VNET: Workload networks with User Defined Routes (UDR) to hub NVAs
# - Internal Load Balancer: Active/active HA for CE instances
# - F5 XC Registration: Automated CE registration with F5 XC Console
#
# User Story 1 MVP: Initial CE deployment with hub-and-spoke and CI/CD

# Azure Resource Group for Infrastructure
# NOTE: This is DIFFERENT from the backend storage resource group
# - Backend RG: {username}-{tenant}-{repo}-tfstate (managed by setup-backend.sh, stores Terraform state)
# - Infrastructure RG: {username}-{tenant}-{repo}-infra (managed by Terraform, holds CE/VNET/LB resources)
# This separation prevents circular dependency where Terraform manages the RG storing its own state
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
  # Reference: https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/reference/ce-site-size-ref
  ce_vm_size_map = {
    medium = "Standard_D8_v4"  # 8 vCPUs, 32 GB RAM
    large  = "Standard_D16_v4" # 16 vCPUs, 64 GB RAM
  }

  ce_vm_size = local.ce_vm_size_map[var.ce_site_size]

  # Identity information for F5 XC site labels and naming
  github_user = "robinmordasiewicz"
  github_repo = "f5-xc-ce-terraform"
  azure_user  = "r.mordasiewicz"

  # F5 XC site naming with owner identifier
  f5xc_site_name = "${local.github_user}-f5xc-azure-${var.azure_region}"

  # Comprehensive site labels for traceability
  site_labels = {
    owner             = local.azure_user
    github_user       = local.github_user
    github_repo       = local.github_repo
    repo_url          = "github.com-${local.github_user}-${local.github_repo}"
    environment       = var.tags["environment"]
    azure_region      = var.azure_region
    deployment_method = "terraform"
    managed_by        = "terraform"
  }
}

# T031-T035: Hub VNET Module
# NOTE: Hub uses generic naming (no F5 XC branding) as it can host multiple security devices
module "hub_vnet" {
  source = "../../modules/azure-hub-vnet"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vnet_name           = "hub-vnet" # Generic hub naming (not F5 XC specific)
  address_space       = var.hub_vnet_address_space
  nva_subnet_prefix   = var.hub_nva_subnet_prefix
  mgmt_subnet_prefix  = var.hub_mgmt_subnet_prefix

  tags = var.tags
}

# T036-T040: Spoke VNET Module
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

# T041-T045: Load Balancer Module
# Azure CAF naming: lbi- prefix for internal load balancer
module "load_balancer" {
  source = "../../modules/azure-load-balancer"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  lb_name             = "lbi-${var.prefix}" # lbi-f5-xc-ce (Azure CAF: internal LB)
  subnet_id           = module.hub_vnet.nva_subnet_id
  frontend_ip_address = var.lb_frontend_ip

  tags = var.tags

  depends_on = [module.hub_vnet]
}

# T046-T050: F5 XC Registration Module
# Site name includes owner identifier for traceability
module "f5_xc_registration" {
  source = "../../modules/f5-xc-registration"

  site_name           = local.f5xc_site_name # robinmordasiewicz-f5xc-azure-eastus
  namespace           = var.f5_xc_namespace
  azure_region        = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  vnet_name           = module.hub_vnet.vnet_name
  subnet_name         = "snet-hub-external" # Updated to Azure CAF naming
  site_labels         = local.site_labels   # Includes owner, repo, etc.

  depends_on = [module.hub_vnet]
}

# T051-T065: CE AppStack Module (Instance 1)
# VM naming: f5-xc-ce-vm-01 (clear F5 XC identification)
module "ce_appstack_1" {
  source = "../../modules/f5-xc-ce-appstack"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vm_name             = "${var.prefix}-vm-01" # f5-xc-ce-vm-01
  vm_size             = local.ce_vm_size
  subnet_id           = module.hub_vnet.nva_subnet_id
  registration_token  = module.f5_xc_registration.registration_token
  ssh_public_key      = local.ssh_public_key
  lb_backend_pool_id  = module.load_balancer.backend_pool_id
  availability_zone   = "1"

  tags = var.tags

  depends_on = [
    module.f5_xc_registration,
    module.load_balancer
  ]
}

# CE AppStack Module (Instance 2 - for HA)
module "ce_appstack_2" {
  source = "../../modules/f5-xc-ce-appstack"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vm_name             = "${var.prefix}-vm-02" # f5-xc-ce-vm-02
  vm_size             = local.ce_vm_size
  subnet_id           = module.hub_vnet.nva_subnet_id
  registration_token  = module.f5_xc_registration.registration_token
  ssh_public_key      = local.ssh_public_key
  lb_backend_pool_id  = module.load_balancer.backend_pool_id
  availability_zone   = "2"

  tags = var.tags

  depends_on = [
    module.f5_xc_registration,
    module.load_balancer
  ]
}

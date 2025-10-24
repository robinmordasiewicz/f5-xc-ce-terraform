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

# Azure Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
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
}

# T031-T035: Hub VNET Module
module "hub_vnet" {
  source = "../../modules/azure-hub-vnet"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vnet_name           = "${var.prefix}-hub-vnet"
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
module "load_balancer" {
  source = "../../modules/azure-load-balancer"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  lb_name             = "${var.prefix}-ce-lb"
  subnet_id           = module.hub_vnet.nva_subnet_id
  frontend_ip_address = var.lb_frontend_ip

  tags = var.tags

  depends_on = [module.hub_vnet]
}

# T046-T050: F5 XC Registration Module
module "f5_xc_registration" {
  source = "../../modules/f5-xc-registration"

  site_name           = "${var.prefix}-ce-site"
  namespace           = var.f5_xc_namespace
  azure_region        = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  vnet_name           = module.hub_vnet.vnet_name
  subnet_name         = "nva-subnet"

  depends_on = [module.hub_vnet]
}

# T051-T065: CE AppStack Module (Instance 1)
module "ce_appstack_1" {
  source = "../../modules/f5-xc-ce-appstack"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vm_name             = "${var.prefix}-ce-01"
  vm_size             = var.ce_vm_size
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
  vm_name             = "${var.prefix}-ce-02"
  vm_size             = var.ce_vm_size
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

# Azure Hub VNET Module

Terraform module for creating Azure hub virtual network with subnets for Network Virtual Appliance (NVA) deployment.

## Overview

This module creates the hub VNET in a hub-and-spoke topology, with dedicated subnets for:
- **NVA Subnet**: Hosts F5 XC CE AppStack instances (minimum /26)
- **Management Subnet**: Operational access and management

## Usage

```hcl
module "hub_vnet" {
  source = "../../modules/azure-hub-vnet"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  vnet_name           = "hub-vnet"
  address_space       = ["10.0.0.0/16"]

  nva_subnet_prefix  = "10.0.1.0/26"
  mgmt_subnet_prefix = "10.0.2.0/24"

  tags = var.common_tags
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.6.0 |
| azurerm | ~> 3.80 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| resource_group_name | Name of the Azure resource group | `string` | n/a | yes |
| location | Azure region for resources | `string` | n/a | yes |
| vnet_name | Name of the hub virtual network | `string` | n/a | yes |
| address_space | Address space for the hub VNET | `list(string)` | n/a | yes |
| nva_subnet_name | Name of the NVA subnet | `string` | `"nva-subnet"` | no |
| nva_subnet_prefix | Address prefix for NVA subnet (minimum /26) | `string` | n/a | yes |
| mgmt_subnet_name | Name of the management subnet | `string` | `"management-subnet"` | no |
| mgmt_subnet_prefix | Address prefix for management subnet | `string` | n/a | yes |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| vnet_id | ID of the hub virtual network |
| vnet_name | Name of the hub virtual network |
| nva_subnet_id | ID of the NVA subnet |
| mgmt_subnet_id | ID of the management subnet |
| address_space | Address space of the hub VNET |

## Resources Created

- Azure Virtual Network (hub)
- Subnet (NVA)
- Subnet (management)
- Network Security Groups
- Route Tables

## Implementation Status

**Phase 2**: Module structure created
**Phase 3**: Implementation (User Story 1, Tasks T031-T035)

# Azure Spoke VNET Module

Creates spoke virtual network with VNET peering to hub and routing through hub NVA.

## Usage

```hcl
module "spoke_vnet" {
  source = "../../modules/azure-spoke-vnet"

  resource_group_name     = azurerm_resource_group.main.name
  location                = var.location
  vnet_name               = "spoke-vnet"
  address_space           = ["10.1.0.0/16"]
  workload_subnet_prefix  = "10.1.1.0/24"
  hub_vnet_id             = module.hub_vnet.vnet_id
  hub_nva_ip              = "10.0.1.4"

  tags = var.common_tags
}
```

## Implementation Status

**Phase 2**: Module structure created
**Phase 3**: Implementation (User Story 1)

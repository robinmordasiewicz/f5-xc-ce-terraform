# Data Model: F5 XC CE CI/CD Automation

**Date**: 2025-10-21
**Feature**: 001-ce-cicd-automation
**Purpose**: Define infrastructure entities, their attributes, relationships, and state management

## Overview

This data model describes the infrastructure entities managed by Terraform for F5 XC CE deployment in Azure hub-and-spoke architecture. All entities are declarative infrastructure-as-code resources with Terraform-managed lifecycle.

---

## Entity 1: Hub Virtual Network

### Purpose
Azure VNET hosting CE AppStack NVA instances with internal load balancer for high availability.

### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| name | string | Yes | Hub VNET name | Must match Azure naming: `^[a-zA-Z0-9-_]{1,64}$` |
| resource_group_name | string | Yes | Azure RG containing VNET | Must exist before VNET creation |
| location | string | Yes | Azure region | Must support F5 XC CE deployment |
| address_space | list(string) | Yes | CIDR blocks for VNET | Minimum `/24`, no overlap with spoke VNETs |
| nva_subnet_prefix | string | Yes | CIDR for NVA subnet | Must be `/26` or larger (per requirements) |
| mgmt_subnet_prefix | string | Yes | CIDR for management subnet | Minimum `/28` for operational access |
| tags | map(string) | No | Azure resource tags | Include `environment`, `managed_by`, `cost_center` |

### Relationships

- **Contains**: 2+ subnets (NVA subnet, management subnet)
- **Hosts**: CE AppStack instances (2 for HA)
- **Peers with**: Spoke VNETs (non-transitive peering)
- **Contains**: Internal Load Balancer for CE NVA HA

### State Transitions

```
[Planned] --terraform apply--> [Creating] --provisioning complete--> [Active]
[Active] --terraform destroy--> [Destroying] --deletion complete--> [Deleted]
[Active] --address space change--> [Updating] --update complete--> [Active]
```

### Validation Rules

- Address space must not overlap with any existing VNET
- NVA subnet must have sufficient IPs for 2+ CE instances + load balancer
- Management subnet must allow inbound SSH/HTTPS from operator IPs
- DNS servers must be specified if custom DNS required

### Terraform Resource Mapping

```hcl
resource "azurerm_virtual_network" "hub" {
  name                = var.hub_vnet_name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.hub_address_space

  tags = merge(var.common_tags, {
    network_type = "hub"
    nva_enabled  = "true"
  })
}

resource "azurerm_subnet" "nva" {
  name                 = "nva-subnet"
  resource_group_name  = azurerm_virtual_network.hub.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.nva_subnet_prefix]
}

resource "azurerm_subnet" "mgmt" {
  name                 = "mgmt-subnet"
  resource_group_name  = azurerm_virtual_network.hub.resource_group_name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [var.mgmt_subnet_prefix]
}
```

---

## Entity 2: Spoke Virtual Network

### Purpose
Azure VNET hosting CE Managed Kubernetes and application workloads, with routing through hub NVA.

### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| name | string | Yes | Spoke VNET name | Must match Azure naming: `^[a-zA-Z0-9-_]{1,64}$` |
| resource_group_name | string | Yes | Azure RG containing VNET | Can be same or different from hub RG |
| location | string | Yes | Azure region | Must match hub VNET region for peering |
| address_space | list(string) | Yes | CIDR blocks for VNET | No overlap with hub or other spokes |
| workload_subnet_prefix | string | Yes | CIDR for K8s workloads | Minimum `/24` for pod IP allocation |
| service_subnet_prefix | string | Yes | CIDR for Azure services | Minimum `/27` for service endpoints |
| hub_vnet_id | string | Yes | Resource ID of hub VNET | For peering relationship |
| hub_nva_sli_ip | string | Yes | IP of hub NVA SLI interface | For UDR next-hop configuration |
| tags | map(string) | No | Azure resource tags | Include workload classification tags |

### Relationships

- **Peers with**: Hub VNET (with `allow_forwarded_traffic = true`)
- **Routes through**: Hub NVA via UDR (default route to SLI IP)
- **Hosts**: CE Managed Kubernetes cluster
- **Contains**: Application workload subnets

### State Transitions

```
[Planned] --terraform apply--> [Creating] --provisioning complete--> [Active]
[Active] --peering established--> [Peered]
[Peered] --UDR applied--> [Routing via Hub]
[Active] --terraform destroy--> [Destroying] --deletion complete--> [Deleted]
```

### Validation Rules

- Must be in same Azure region as hub VNET for peering
- Address space must not overlap with hub or other spokes
- Peering must have `allow_forwarded_traffic = true` for hub NVA routing
- UDR must point default route (0.0.0.0/0) to hub NVA SLI IP
- Workload subnet must have sufficient IPs for K8s cluster (pods + nodes)

### Terraform Resource Mapping

```hcl
resource "azurerm_virtual_network" "spoke" {
  name                = var.spoke_vnet_name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.spoke_address_space

  tags = merge(var.common_tags, {
    network_type = "spoke"
    peered_to_hub = azurerm_virtual_network.hub.name
  })
}

resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "${var.spoke_vnet_name}-to-${var.hub_vnet_name}"
  resource_group_name       = azurerm_virtual_network.spoke.resource_group_name
  virtual_network_name      = azurerm_virtual_network.spoke.name
  remote_virtual_network_id = var.hub_vnet_id

  allow_forwarded_traffic = true
  allow_gateway_transit   = false
  use_remote_gateways     = false
}

resource "azurerm_route_table" "spoke" {
  name                = "${var.spoke_vnet_name}-rt"
  location            = var.location
  resource_group_name = var.resource_group_name

  route {
    name                   = "default-via-hub-nva"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = var.hub_nva_sli_ip
  }
}

resource "azurerm_subnet_route_table_association" "spoke_workload" {
  subnet_id      = azurerm_subnet.spoke_workload.id
  route_table_id = azurerm_route_table.spoke.id
}
```

---

## Entity 3: CE AppStack Instance (Hub NVA)

### Purpose
F5 Distributed Cloud Customer Edge running as Secure Mesh Site in hub VNET, providing Layer 3/4 network security and service mesh capabilities.

### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| name | string | Yes | CE instance name | Must be unique in F5 XC tenant |
| vm_size | string | Yes | Azure VM SKU | Mapped from ce_site_size: medium=`Standard_D8_v4`, large=`Standard_D16_v4` |
| os_disk_size_gb | number | Yes | OS disk size | Minimum: 80 GB |
| sli_subnet_id | string | Yes | Subnet for inside interface (SLI) | Must be in NVA subnet |
| slo_subnet_id | string | Yes | Subnet for outside interface (SLO) | Can be same as SLI or separate |
| mgmt_subnet_id | string | Yes | Subnet for management interface | Must be in management subnet |
| registration_token | string | Yes | F5 XC registration token | Sensitive, from volterra provider |
| admin_password | string | Yes | Admin password for CE | Minimum 12 chars, meets complexity |
| availability_zone | number | No | Azure AZ for deployment | 1, 2, or 3 for HA across zones |
| backend_pool_id | string | Yes | Load balancer backend pool | For HA configuration |
| tags | map(string) | No | Azure resource tags | Include CE site name, F5 XC tenant |

### Relationships

- **Registered with**: F5 XC Console (via registration token)
- **Member of**: Azure Load Balancer backend pool
- **Connected to**: 3 network interfaces (SLI, SLO, management)
- **Routes traffic for**: Spoke VNETs (via UDR next-hop)
- **Managed by**: F5 XC Global Controller

### State Transitions

```
[Token Generated] --VM deployed--> [Provisioned]
[Provisioned] --cloud-init runs--> [Registering]
[Registering] --registration success--> [Online]
[Online] --health probe pass--> [Active in LB]
[Active in LB] --serving traffic--> [Operational]
[Operational] --terraform destroy--> [Deregistering]
[Deregistering] --VM deleted--> [Deleted]
```

### Validation Rules

- VM size must meet minimum CE requirements (8 vCPUs, 32 GB RAM)
- OS disk must be at least 80 GB
- All 3 NICs must be in correct subnets (SLI in NVA, management in mgmt)
- Registration token must be valid and not expired
- CE must successfully register before marking deployment complete
- Health probe endpoint must respond within 5 seconds

### Terraform Resource Mapping

```hcl
resource "azurerm_linux_virtual_machine" "ce_appstack" {
  name                = var.ce_instance_name
  resource_group_name = var.resource_group_name
  location            = var.location
  size                = var.vm_size
  zone                = var.availability_zone

  admin_username = "admin"
  admin_password = var.admin_password
  disable_password_authentication = false

  network_interface_ids = [
    azurerm_network_interface.sli.id,
    azurerm_network_interface.slo.id,
    azurerm_network_interface.mgmt.id,
  ]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.os_disk_size_gb
  }

  source_image_reference {
    publisher = "f5-networks"
    offer     = "f5-xc-customer-edge"
    sku       = "appstack"
    version   = "latest"
  }

  plan {
    publisher = "f5-networks"
    product   = "f5-xc-customer-edge"
    name      = "appstack"
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    registration_token = var.registration_token
    site_name          = var.ce_instance_name
  }))

  tags = merge(var.common_tags, {
    ce_role = "hub-nva"
    f5_xc_site = var.ce_instance_name
  })
}
```

---

## Entity 4: CE Managed Kubernetes Instance (Spoke)

### Purpose
F5 Distributed Cloud Customer Edge running Managed Kubernetes in spoke VNET for application workload orchestration.

### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| name | string | Yes | CE K8s cluster name | Must be unique in F5 XC tenant |
| vm_size | string | Yes | Azure VM SKU | Mapped from ce_site_size: medium=`Standard_D8_v4`, large=`Standard_D16_v4` |
| os_disk_size_gb | number | Yes | OS disk size | Minimum: 80 GB, recommend 100+ for K8s |
| node_subnet_id | string | Yes | Subnet for K8s nodes | Must be in spoke workload subnet |
| registration_token | string | Yes | F5 XC registration token | Sensitive, from volterra provider |
| admin_password | string | Yes | Admin password for CE | Minimum 12 chars, meets complexity |
| availability_zone | number | No | Azure AZ for deployment | 1, 2, or 3 for HA |
| k8s_cluster_name | string | Yes | Kubernetes cluster name | Unique within F5 XC tenant |
| tags | map(string) | No | Azure resource tags | Include cluster name, workload type |

### Relationships

- **Registered with**: F5 XC Console (via registration token)
- **Deployed in**: Spoke VNET workload subnet
- **Routes through**: Hub NVA (via spoke UDR)
- **Hosts**: Kubernetes pods and services
- **Managed by**: F5 XC Managed Kubernetes

### State Transitions

```
[Token Generated] --VM deployed--> [Provisioned]
[Provisioned] --cloud-init runs--> [Registering]
[Registering] --registration success--> [Online]
[Online] --K8s control plane ready--> [Cluster Ready]
[Cluster Ready] --pods deployed--> [Operational]
[Operational] --terraform destroy--> [Deregistering]
[Deregistering] --VM deleted--> [Deleted]
```

### Validation Rules

- VM size must meet minimum CE K8s requirements (8 vCPUs, 32 GB RAM)
- OS disk must be at least 80 GB (recommend 100+ for K8s etcd and images)
- Node subnet must have sufficient IPs for cluster nodes and pod CIDR
- Registration token must be valid and not expired
- CE must successfully register and K8s cluster must be ready before completion
- Default route must point to hub NVA SLI IP

### Terraform Resource Mapping

```hcl
resource "azurerm_linux_virtual_machine" "ce_k8s" {
  name                = var.ce_k8s_name
  resource_group_name = var.resource_group_name
  location            = var.location
  size                = var.vm_size
  zone                = var.availability_zone

  admin_username = "admin"
  admin_password = var.admin_password
  disable_password_authentication = false

  network_interface_ids = [
    azurerm_network_interface.k8s_node.id,
  ]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.os_disk_size_gb
  }

  source_image_reference {
    publisher = "f5-networks"
    offer     = "f5-xc-customer-edge"
    sku       = "k8s"
    version   = "latest"
  }

  plan {
    publisher = "f5-networks"
    product   = "f5-xc-customer-edge"
    name      = "k8s"
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    registration_token = var.registration_token
    cluster_name       = var.k8s_cluster_name
  }))

  tags = merge(var.common_tags, {
    ce_role = "managed-k8s"
    k8s_cluster = var.k8s_cluster_name
  })
}
```

---

## Entity 5: Azure Internal Load Balancer

### Purpose
Provides high availability for CE AppStack NVA instances in hub VNET with health probes and traffic distribution.

### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| name | string | Yes | Load balancer name | Must match Azure naming conventions |
| resource_group_name | string | Yes | Azure RG containing LB | Same as hub VNET RG |
| location | string | Yes | Azure region | Must match hub VNET region |
| frontend_ip_name | string | Yes | Frontend IP configuration name | Descriptive name for SLI frontend |
| frontend_ip_address | string | No | Static IP for frontend | Must be in NVA subnet range |
| subnet_id | string | Yes | Subnet for frontend IP | Must be NVA subnet |
| backend_pool_name | string | Yes | Backend pool name | Contains CE NVA instances |
| health_probe_port | number | Yes | Port for health probe | Typically 65500 for CE |
| health_probe_protocol | string | Yes | Health probe protocol | HTTP or TCP |
| load_balancing_rules | list(object) | Yes | LB rules for traffic | Define port, protocol, backend port |
| sku | string | Yes | LB SKU | "Standard" for zone redundancy |
| tags | map(string) | No | Azure resource tags | Include HA role, NVA function |

### Relationships

- **Deployed in**: Hub VNET NVA subnet
- **Frontend**: Single IP in NVA subnet (target for spoke UDR)
- **Backend**: CE AppStack instances in pool
- **Health Probes**: Monitor CE instance health
- **Load Balancing Rules**: Distribute traffic to healthy backends

### State Transitions

```
[Planned] --terraform apply--> [Creating]
[Creating] --LB provisioned--> [Active]
[Active] --backends added--> [Backend Pool Configured]
[Backend Pool Configured] --probes passing--> [Load Balancing]
[Load Balancing] --terraform destroy--> [Deleting]
[Deleting] --deletion complete--> [Deleted]
```

### Validation Rules

- Frontend IP must be in NVA subnet IP range
- Backend pool must contain at least 2 CE instances for HA
- Health probe must successfully check CE instance health
- Load balancing rules must not conflict with CE required ports
- SKU must be "Standard" for zone redundancy support

### Terraform Resource Mapping

```hcl
resource "azurerm_lb" "hub_nva" {
  name                = var.lb_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"

  frontend_ip_configuration {
    name                          = var.frontend_ip_name
    subnet_id                     = var.nva_subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.frontend_ip_address
  }

  tags = merge(var.common_tags, {
    ha_role = "nva-load-balancer"
  })
}

resource "azurerm_lb_backend_address_pool" "ce_pool" {
  name            = var.backend_pool_name
  loadbalancer_id = azurerm_lb.hub_nva.id
}

resource "azurerm_lb_probe" "ce_health" {
  name                = "ce-health-probe"
  loadbalancer_id     = azurerm_lb.hub_nva.id
  protocol            = var.health_probe_protocol
  port                = var.health_probe_port
  interval_in_seconds = 5
  number_of_probes    = 2
}

resource "azurerm_lb_rule" "ce_lb_rule" {
  name                           = "ce-all-ports"
  loadbalancer_id                = azurerm_lb.hub_nva.id
  protocol                       = "All"
  frontend_port                  = 0
  backend_port                   = 0
  frontend_ip_configuration_name = azurerm_lb.hub_nva.frontend_ip_configuration[0].name
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.ce_pool.id]
  probe_id                       = azurerm_lb_probe.ce_health.id
  enable_floating_ip             = true
}
```

---

## Entity 6: F5 XC Site Registration

### Purpose
Represents F5 XC site configuration and generates registration token for CE instance auto-registration.

### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| name | string | Yes | Site name in F5 XC Console | Must be unique in tenant |
| namespace | string | Yes | F5 XC namespace | Typically "system" for sites |
| azure_region | string | Yes | Azure region name | Must match Azure location |
| resource_group | string | Yes | Azure RG name | Where CE VM will be deployed |
| vnet_name | string | Yes | Azure VNET name | Hub or spoke VNET name |
| site_type | string | Yes | CE site type | "secure_mesh_site" or "k8s_site" |
| ce_certified_hardware | string | Yes | Hardware certification | "azure-byol" for BYOL deployment |
| labels | map(string) | No | Site labels | For organization and filtering |

### Relationships

- **Creates**: Registration token (output, sensitive)
- **Consumed by**: CE instance deployment (cloud-init)
- **Managed in**: F5 XC Console (via volterra provider)
- **References**: Azure infrastructure (RG, VNET)

### State Transitions

```
[Planned] --volterra provider--> [Creating Site]
[Creating Site] --site created--> [Token Generated]
[Token Generated] --used in cloud-init--> [CE Registering]
[CE Registering] --registration success--> [Site Online]
[Site Online] --terraform destroy--> [Deregistering]
[Deregistering] --site deleted--> [Deleted]
```

### Validation Rules

- Site name must be unique within F5 XC tenant
- Azure region must be supported by F5 XC
- Registration token must be treated as sensitive (never logged)
- Site must remain in F5 XC Console until CE is deregistered
- Token expires after 30 days if unused

### Terraform Resource Mapping

```hcl
resource "volterra_azure_vnet_site" "hub_ce" {
  name      = var.site_name
  namespace = "system"

  azure_region = var.azure_region
  resource_group = var.resource_group_name
  vnet {
    existing_vnet {
      vnet_name = var.vnet_name
      resource_group = var.resource_group_name
    }
  }

  machine_type = var.vm_size
  disk_size    = var.os_disk_size_gb

  ingress_gw {
    azure_certified_hw = "azure-byol"

    azure_vnet_config {
      sli_config {
        subnet {
          subnet_name = var.sli_subnet_name
        }
      }
      slo_config {
        subnet {
          subnet_name = var.slo_subnet_name
        }
      }
    }
  }

  labels = var.site_labels
}

output "registration_token" {
  value     = volterra_azure_vnet_site.hub_ce.registration_token
  sensitive = true
}
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    F5 XC Console (External)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  F5 XC Site Registration                                  │   │
│  │  - Generates registration token                           │   │
│  │  - Manages CE site configuration                          │   │
│  └──────────────┬───────────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────────┘
                  │ Registration Token (sensitive)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Azure Subscription                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Hub VNET                                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │ NVA Subnet   │  │ Mgmt Subnet  │  │ Internal LB     │  │ │
│  │  │  /26         │  │  /24         │  │ - Frontend IP   │  │ │
│  │  │              │  │              │  │ - Backend Pool  │  │ │
│  │  │  CE Instance │  │              │  │ - Health Probes │  │ │
│  │  │  #1 (AppStack│  │              │  └─────────────────┘  │ │
│  │  │   - SLI NIC) │  │              │           │           │ │
│  │  │              │  │              │           │           │ │
│  │  │  CE Instance │  │              │  ┌────────▼────────┐  │ │
│  │  │  #2 (AppStack│◄─┼──────────────┼──┤ Backend Pool    │  │ │
│  │  │   - SLI NIC) │  │              │  │ (2 CE instances)│  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │ │
│  └──────────────┬───────────────────────────────────────────┬─┘ │
│                 │ VNET Peering (non-transitive)             │   │
│                 ▼                                            │   │
│  ┌────────────────────────────────────────────────────────┐ │   │
│  │  Spoke VNET                                             │ │   │
│  │  ┌──────────────────┐  ┌───────────────────────────┐   │ │   │
│  │  │ Workload Subnet  │  │ Service Subnet            │   │ │   │
│  │  │  /24             │  │  /27                      │   │ │   │
│  │  │                  │  │                           │   │ │   │
│  │  │  CE Instance     │  │  Azure Services           │   │ │   │
│  │  │  (K8s)           │  │  (Storage, Key Vault)     │   │ │   │
│  │  │  - Node NICs     │  │                           │   │ │   │
│  │  │  - Pod Network   │  │                           │   │ │   │
│  │  └──────────────────┘  └───────────────────────────┘   │ │   │
│  │                                                          │ │   │
│  │  Route Table:                                           │ │   │
│  │  - 0.0.0.0/0 → Hub NVA SLI IP (10.0.1.4)               │ │   │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘

Legend:
  ─  : Relationship/Connection
  ►  : Data flow direction
  ┌─┐: Entity boundary
  []: External system
```

---

## State Management

All entities are managed as Terraform resources with state stored in Azure Blob Storage:

**State File Structure:**
```
tfstate (blob container)
└── 001-ce-cicd-automation.tfstate
    ├── azurerm_virtual_network.hub
    ├── azurerm_virtual_network.spoke
    ├── azurerm_lb.hub_nva
    ├── azurerm_linux_virtual_machine.ce_appstack_1
    ├── azurerm_linux_virtual_machine.ce_appstack_2
    ├── azurerm_linux_virtual_machine.ce_k8s
    └── volterra_azure_vnet_site.hub_ce
```

**State Locking:**
- Blob lease mechanism prevents concurrent modifications
- Lock automatically released after terraform operation completes
- Failed operations may require manual lease break

**State Encryption:**
- Azure Storage Service Encryption (SSE) with managed keys
- State file contains sensitive data (passwords, tokens)
- Access controlled via Azure RBAC

---

## Summary

This data model defines 6 core infrastructure entities with clear relationships, state transitions, and validation rules. All entities are declarative Terraform resources following infrastructure-as-code principles with immutable deployments managed through GitOps workflow.

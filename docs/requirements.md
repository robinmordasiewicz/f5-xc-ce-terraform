# System Requirements

This document details the system requirements, prerequisites, and resource specifications for deploying F5 XC Customer Edge to Azure.

## Table of Contents

- [Azure Prerequisites](#azure-prerequisites)
- [F5 XC Prerequisites](#f5-xc-prerequisites)
- [GitHub Prerequisites](#github-prerequisites)
- [F5 XC Customer Edge Specifications](#f5-xc-customer-edge-specifications)
- [Azure Resource Specifications](#azure-resource-specifications)
- [Network Requirements](#network-requirements)
- [Development Prerequisites](#development-prerequisites)

## Azure Prerequisites

### Azure Subscription

- **Subscription Access**: Contributor role or higher
- **Resource Quotas**:
  - Standard_D8s_v3 VMs: Minimum 4 cores available (2 per CE node)
  - Public IPs: 2 available (if using public endpoints)
  - VNETs: 2 available (hub and spoke)
  - Load Balancers: 1 available

### Azure Service Principal

For GitHub Actions automation:

- **Identity Type**: Workload identity federation (recommended) or service principal
- **Required Permissions**:
  - Contributor on target resource group(s)
  - User Access Administrator (for role assignments)
  - Storage Blob Data Contributor (for Terraform state)

### Azure Resources for Backend

The following resources must be created before deployment (via `setup-backend.sh`):

- **Resource Group**: For Terraform state storage
- **Storage Account**: For remote state with:
  - Blob versioning enabled
  - Soft delete enabled
  - Encryption at rest
  - Network access configured
- **Storage Container**: Named `tfstate`

### Azure CLI

- **Version**: >= 2.45.0
- **Purpose**: Backend setup and local development
- **Installation**: https://docs.microsoft.com/cli/azure/install-azure-cli

## F5 XC Prerequisites

### F5 XC Account

- **Account Type**: F5 Distributed Cloud tenant
- **Access Level**: Admin or Site Admin role
- **Registration**: https://www.f5.com/cloud

### F5 XC API Credentials

- **API Token**: Required for site registration and management
- **Scope**: Full API access
- **Generation**: Console → Account Settings → API Credentials
- **Security**: Store in GitHub Secrets, never commit to repository

### F5 XC Tenant Configuration

- **Namespace**: Default or custom namespace for CE sites
- **Site Settings**: Hub and spoke site configurations
- **Network Settings**: Site local inside/outside network configuration

## GitHub Prerequisites

### GitHub Repository

- **Repository Access**: Admin access for Actions configuration
- **Actions**: GitHub Actions enabled
- **Branch Protection**: Main branch protection recommended

### GitHub Secrets

The following secrets must be configured in repository settings:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AZURE_CLIENT_ID` | Azure AD application ID | `00000000-0000-0000-0000-000000000000` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `00000000-0000-0000-0000-000000000000` |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription | `00000000-0000-0000-0000-000000000000` |
| `F5_XC_API_TOKEN` | F5 XC Console API token | `xxxx-xxxx-xxxx-xxxx` |

**Security Note**: Use workload identity federation instead of client secrets where possible.

### GitHub Actions

- **Workflow Permissions**: Read and write permissions
- **OIDC Provider**: Configured for workload identity (if used)
- **Runner**: GitHub-hosted runners (ubuntu-latest)

## F5 XC Customer Edge Specifications

### CE AppStack (Hub NVA)

Minimum specifications per node:

| Resource | Specification | Notes |
|----------|---------------|-------|
| **CPU** | 8 vCPUs | Per CE AppStack node |
| **Memory** | 32 GB RAM | Per CE AppStack node |
| **Storage** | 80 GB disk | Premium SSD recommended |
| **Network** | 1 NIC | Connected to hub subnet |
| **Bandwidth** | 10 Gbps | Accelerated networking enabled |

**Recommended Azure VM SKU**: Standard_D8s_v3 or higher

**High Availability**:
- Minimum 2 nodes for HA
- 3 nodes recommended for production
- Distributed across availability zones

### CE Managed Kubernetes (Spoke)

Minimum specifications per node:

| Resource | Specification | Notes |
|----------|---------------|-------|
| **CPU** | 8 vCPUs | Per Kubernetes node |
| **Memory** | 32 GB RAM | Per Kubernetes node |
| **Storage** | 80 GB disk | Premium SSD for etcd |
| **Network** | 1 NIC | Connected to spoke subnet |
| **Bandwidth** | 10 Gbps | Accelerated networking enabled |

**Recommended Azure VM SKU**: Standard_D8s_v3 or higher

**Cluster Sizing**:
- Minimum 1 node for development
- 3 nodes recommended for production
- Scale based on workload requirements

## Azure Resource Specifications

### Hub VNET

| Setting | Specification | Notes |
|---------|---------------|-------|
| **Address Space** | /16 CIDR block | e.g., 10.0.0.0/16 |
| **NVA Subnet** | /26 subnet | Minimum for CE AppStack |
| **Gateway Subnet** | /27 subnet | If using VPN/ExpressRoute |
| **Region** | Azure region | Choose based on latency requirements |

**Example Hub VNET**:
```
Hub VNET: 10.0.0.0/16
├── NVA Subnet: 10.0.0.0/26 (64 addresses)
└── Gateway Subnet: 10.0.1.0/27 (32 addresses)
```

### Spoke VNET

| Setting | Specification | Notes |
|---------|---------------|-------|
| **Address Space** | /16 CIDR block | e.g., 10.1.0.0/16 |
| **Workload Subnets** | /24 subnets | Multiple subnets as needed |
| **VNET Peering** | To hub VNET | Required for connectivity |
| **Region** | Same as hub | For optimal latency |

**Example Spoke VNET**:
```
Spoke VNET: 10.1.0.0/16
├── K8s Nodes Subnet: 10.1.0.0/24 (256 addresses)
├── K8s Pods Subnet: 10.1.1.0/24 (256 addresses)
└── K8s Services Subnet: 10.1.2.0/24 (256 addresses)
```

### Azure Load Balancer

| Setting | Specification | Notes |
|---------|---------------|-------|
| **SKU** | Standard | Required for zone redundancy |
| **Type** | Internal | Private IP in hub subnet |
| **Frontend IP** | Static private IP | From hub NVA subnet |
| **Backend Pool** | CE AppStack instances | All HA nodes |
| **Health Probe** | TCP port 65500 | CE management port |
| **Load Balancing Rule** | All ports | HA ports rule |

### Storage Account (Terraform State)

| Setting | Specification | Notes |
|---------|---------------|-------|
| **SKU** | Standard_LRS or Standard_ZRS | ZRS for zone redundancy |
| **Kind** | StorageV2 | General purpose v2 |
| **Versioning** | Enabled | State history |
| **Soft Delete** | Enabled (7-30 days) | Accidental deletion protection |
| **Encryption** | Microsoft-managed keys | Or customer-managed |
| **Network** | Private endpoint | Or service endpoint |

## Network Requirements

### Outbound Connectivity

CE nodes require outbound internet access to:

| Destination | Port | Protocol | Purpose |
|-------------|------|----------|---------|
| `*.console.ves.volterra.io` | 443 | HTTPS | Control plane communication |
| `*.ves.volterra.io` | 443 | HTTPS | API and data plane |
| `*.blob.core.windows.net` | 443 | HTTPS | Azure storage (if used) |
| NTP servers | 123 | UDP | Time synchronization |
| DNS servers | 53 | UDP/TCP | Name resolution |

### Network Security Groups

Recommended NSG rules:

**Hub NVA Subnet**:
- Inbound: Allow from spoke subnets
- Outbound: Allow to internet, spoke subnets
- Management: Allow from bastion or VPN

**Spoke Workload Subnet**:
- Inbound: Allow from application sources
- Outbound: Allow via hub NVA
- Management: Allow from bastion or VPN

### DNS Requirements

- **Azure DNS**: Use Azure-provided DNS or custom
- **F5 XC Sites**: Must resolve public F5 XC endpoints
- **Internal Names**: Custom DNS for internal resources

## Development Prerequisites

For local development and testing:

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Terraform** | >= 1.6.0 | Infrastructure provisioning |
| **Azure CLI** | >= 2.45.0 | Azure authentication and management |
| **Git** | >= 2.30 | Version control |
| **pre-commit** | >= 3.0 | Code quality hooks |
| **Python** | >= 3.11 | Pre-commit framework |
| **Go** | >= 1.21 | Integration tests |

### Optional Tools

| Tool | Purpose |
|------|---------|
| **tflint** | Terraform linting |
| **checkov** | Security scanning |
| **yamllint** | YAML validation |
| **shellcheck** | Shell script validation |
| **markdownlint** | Markdown formatting |

### Development Environment

Minimum development machine specifications:

- **OS**: Linux, macOS, or Windows with WSL2
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk**: 20 GB free space
- **Network**: Broadband internet connection

## Sizing Guidelines

### Small Deployment

**Use Case**: Development, testing, proof-of-concept

| Component | Count | VM SKU | Total vCPUs | Total RAM |
|-----------|-------|--------|-------------|-----------|
| CE AppStack | 2 | Standard_D8s_v3 | 16 | 64 GB |
| CE K8s | 1 | Standard_D8s_v3 | 8 | 32 GB |
| **Total** | **3** | - | **24** | **96 GB** |

### Medium Deployment

**Use Case**: Production, moderate workload

| Component | Count | VM SKU | Total vCPUs | Total RAM |
|-----------|-------|--------|-------------|-----------|
| CE AppStack | 3 | Standard_D16s_v3 | 48 | 192 GB |
| CE K8s | 3 | Standard_D8s_v3 | 24 | 96 GB |
| **Total** | **6** | - | **72** | **288 GB** |

### Large Deployment

**Use Case**: Production, high workload, multi-spoke

| Component | Count | VM SKU | Total vCPUs | Total RAM |
|-----------|-------|--------|-------------|-----------|
| CE AppStack | 5 | Standard_D16s_v3 | 80 | 320 GB |
| CE K8s (per spoke) | 5 | Standard_D16s_v3 | 80 | 320 GB |
| **Total (1 spoke)** | **10** | - | **160** | **640 GB** |

## Cost Estimates

Approximate monthly costs (East US region, pay-as-you-go):

### Small Deployment
- **Compute**: ~$1,200/month (3 × D8s_v3)
- **Networking**: ~$50/month (load balancer, bandwidth)
- **Storage**: ~$25/month (managed disks, state storage)
- **Total**: ~$1,275/month

### Medium Deployment
- **Compute**: ~$3,600/month (6 × D8s_v3 equivalent)
- **Networking**: ~$100/month
- **Storage**: ~$50/month
- **Total**: ~$3,750/month

**Cost Optimization**:
- Use reserved instances for 30-40% savings
- Right-size VMs based on actual usage
- Enable auto-shutdown for dev/test environments
- Use Azure Hybrid Benefit if applicable

## Compliance and Security Requirements

### Compliance Frameworks

Supported compliance standards:

- **GDPR**: Data residency and privacy controls
- **HIPAA**: Healthcare data protection (with additional configuration)
- **PCI DSS**: Payment card industry standards
- **SOC 2**: Service organization controls
- **ISO 27001**: Information security management

### Security Requirements

- **Encryption**: All data encrypted at rest and in transit
- **Network Security**: NSGs and NVA filtering on all resources
- **Identity**: Azure AD authentication with RBAC
- **Monitoring**: Azure Monitor and F5 XC observability
- **Compliance**: Regular security scanning and auditing

## Related Documentation

- [Architecture Documentation](architecture.md) - Detailed technical architecture
- [Developer Guide](development.md) - Development environment setup
- [Quickstart Guide](../specs/001-ce-cicd-automation/quickstart.md) - Deployment instructions
- [F5 XC Documentation](https://docs.cloud.f5.com) - Official F5 XC documentation
- [Azure Architecture](https://learn.microsoft.com/azure/architecture/) - Azure best practices

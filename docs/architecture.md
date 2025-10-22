# Architecture Documentation

This document provides detailed technical architecture information for the F5 Distributed Cloud Customer Edge Azure deployment.

## Table of Contents

- [Overview](#overview)
- [Network Architecture](#network-architecture)
- [Component Details](#component-details)
- [High Availability Design](#high-availability-design)
- [Security Architecture](#security-architecture)
- [State Management](#state-management)
- [Automation Pipeline](#automation-pipeline)

## Overview

This project implements infrastructure-as-code (IaC) for deploying F5 XC Customer Edge instances to Azure following hub-and-spoke network architecture with the following key characteristics:

- **Hub VNET**: CE AppStack (Secure Mesh Site) deployed as Network Virtual Appliance (NVA)
- **Spoke VNET**: CE Managed Kubernetes with routing through hub NVA
- **High Availability**: Azure Load Balancer for active/active NVA deployment
- **Automation**: GitHub Actions CI/CD pipeline with workload identity federation
- **State Management**: Azure Blob Storage with encryption and locking

## Network Architecture

### Hub-and-Spoke Topology

```
┌─────────────────────────────────────────────────────────────┐
│                        Hub VNET                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Azure Load Balancer (Internal)                     │   │
│  │         ↓              ↓                             │   │
│  │  CE AppStack 1   CE AppStack 2                      │   │
│  │  (NVA - HA)      (NVA - HA)                         │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ VNET Peering
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                       Spoke VNET                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  CE Managed Kubernetes                              │   │
│  │  (Routes via Hub NVA SLI)                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Hub VNET Design

The hub VNET serves as the central network hub and contains F5 XC CE AppStack nodes deployed as Network Virtual Appliances:

- **Address Space**: /16 CIDR block
- **NVA Subnet**: /26 subnet for CE AppStack nodes
- **Load Balancer**: Internal Azure Load Balancer for NVA high availability
- **Routing**: All spoke traffic routes through hub NVA

**Key Characteristics:**
- Centralized security and traffic inspection
- Shared services location
- High availability with active/active NVA deployment
- Optimized for network throughput

### Spoke VNET Design

The spoke VNET contains workload resources and connects to the hub via VNET peering:

- **Address Space**: /16 CIDR block
- **Workload Type**: F5 XC CE Managed Kubernetes
- **Routing**: User-defined routes (UDR) direct traffic through hub NVA
- **Connectivity**: VNET peering to hub with remote gateway transit

**Key Characteristics:**
- Isolated workload environment
- Secure connectivity via hub NVA
- Scalable architecture for multiple spokes
- Optimized for application workloads

### VNET Peering Configuration

- **Peering Type**: Bidirectional VNET peering
- **Gateway Transit**: Enabled for spoke-to-hub communication
- **Remote Gateway**: Spoke uses hub gateway for external connectivity
- **Forwarded Traffic**: Allowed for spoke-to-hub routing

## Component Details

### F5 XC CE AppStack (Hub NVA)

**Purpose**: Secure Mesh Site providing network security and connectivity services

**Deployment Model**:
- Two instances deployed for high availability
- Active/active configuration with load balancing
- Azure Availability Zones for fault tolerance

**Networking**:
- Single network interface per instance
- Connected to hub NVA subnet
- Fronted by internal load balancer
- Static IP assignment

**Capabilities**:
- Network Virtual Appliance (NVA) functionality
- Layer 3/4 traffic inspection and routing
- F5 XC Secure Mesh Site services
- Integration with F5 XC Global Network

### F5 XC CE Managed Kubernetes (Spoke)

**Purpose**: Kubernetes cluster for containerized application workloads

**Deployment Model**:
- Managed by F5 XC control plane
- Integrated with hub security services
- Routes traffic through hub NVA

**Networking**:
- Connected to spoke VNET
- User-defined routes to hub NVA
- Outbound connectivity via hub
- Pod and service networking

**Capabilities**:
- Kubernetes orchestration
- Container runtime management
- F5 XC integration for security and observability
- Application load balancing

### Azure Load Balancer

**Purpose**: Distribute traffic across CE AppStack NVA instances

**Configuration**:
- **Type**: Internal load balancer
- **SKU**: Standard
- **Frontend IP**: Static private IP in hub subnet
- **Backend Pool**: CE AppStack instances
- **Health Probes**: TCP health checks on CE management port
- **Load Balancing Rules**: All ports forwarding

**High Availability**:
- Active/active traffic distribution
- Automatic failover on health check failure
- Session persistence options
- Zone redundancy

## High Availability Design

### Multi-Instance Deployment

- **CE AppStack**: Minimum 2 instances in hub
- **Availability Zones**: Instances distributed across zones
- **Load Balancing**: Active/active configuration
- **Failover**: Automatic with health check monitoring

### Health Monitoring

- **Load Balancer Probes**: TCP health checks every 5 seconds
- **F5 XC Health**: Platform-level health monitoring
- **Auto-healing**: Unhealthy instances automatically replaced
- **Alerting**: Azure Monitor integration for incident response

### Resilience Characteristics

- **RPO (Recovery Point Objective)**: Near-zero with stateless NVA
- **RTO (Recovery Time Objective)**: < 1 minute with active/active
- **Fault Tolerance**: Single zone failure tolerated
- **Geographic Distribution**: Multi-zone deployment in single region

## Security Architecture

### Network Security

- **Network Segmentation**: Hub-spoke isolation
- **Traffic Inspection**: All spoke traffic through hub NVA
- **Security Groups**: Azure NSGs on all subnets
- **Zero Trust**: Default deny with explicit allow rules

### Identity and Access

- **Workload Identity Federation**: GitHub Actions to Azure
- **RBAC**: Role-based access control for all resources
- **Service Principals**: Managed identities where possible
- **API Authentication**: F5 XC API token management

### Secrets Management

- **Azure Key Vault**: Centralized secret storage
- **Encryption at Rest**: All storage encrypted
- **Encryption in Transit**: TLS for all connections
- **Secret Rotation**: Automated rotation policies

### Compliance

- **Security Scanning**: Checkov for IaC security
- **Secret Detection**: detect-secrets in pre-commit
- **Policy Enforcement**: Azure Policy integration
- **Audit Logging**: Comprehensive audit trails

## Deployment Methods

This project supports two deployment methods, each optimized for different use cases:

### CI/CD Deployment (GitHub Actions)

**Use Case**: Automated production deployments, team collaboration, consistent infrastructure management

**Authentication**: OIDC Workload Identity Federation
- No service principal credentials stored in GitHub
- Uses federated credentials for token exchange
- Azure AD validates GitHub OIDC tokens
- Requires service principal with federated credentials configured

**Prerequisites**:
- Azure service principal with Contributor role
- Service principal with "Storage Blob Data Owner" role on state storage account
- GitHub Actions secrets configured:
  - `AZURE_CLIENT_ID`: Service principal application ID
  - `AZURE_TENANT_ID`: Azure AD tenant ID
  - `AZURE_SUBSCRIPTION_ID`: Target subscription ID
  - `F5_XC_API_TOKEN`: F5 XC Console API token

**Workflow**:
1. GitHub Actions runner requests OIDC token from GitHub
2. Azure AD validates token and issues access token
3. Terraform authenticates to Azure using access token
4. Terraform operations execute with service principal permissions

**Benefits**:
- No credentials stored in GitHub (secure)
- Automated deployment on code changes
- Built-in approval workflows
- Consistent deployment across environments
- Audit trail via GitHub Actions history

### Manual CLI Deployment

**Use Case**: Local development, testing, troubleshooting, learning

**Authentication**: Azure CLI Authentication
- Uses `az login` for interactive authentication
- Leverages existing Azure CLI credentials
- No service principal required (can use user identity)
- Terraform inherits Azure CLI authentication context

**Prerequisites**:
- Azure CLI installed and configured
- User account with required permissions:
  - "Contributor" role on resource group (for deploying resources)
  - "Storage Blob Data Owner" role on state storage account (for state management)
- F5 XC API token

**Workflow**:
1. User runs `az login` for interactive authentication
2. User runs `./scripts/setup-backend.sh` to create state storage
3. User creates `backend.local.hcl` with storage account configuration
4. User runs `terraform init -backend-config=backend.local.hcl`
5. Terraform operations use Azure CLI authentication

**Benefits**:
- Quick setup without service principal configuration
- Ideal for local development and testing
- Direct feedback and control
- Simpler troubleshooting
- No GitHub Actions configuration needed

### Deployment Methods Comparison

| Aspect | CI/CD (OIDC) | Manual CLI |
|--------|--------------|------------|
| **Authentication** | Workload identity federation | Azure CLI (`az login`) |
| **Setup Complexity** | High (service principal + GitHub) | Low (just Azure CLI) |
| **Prerequisites** | Service principal + roles + GitHub secrets | User account + roles |
| **Backend Config** | Environment variables | `backend.local.hcl` file |
| **State Storage** | Azure Blob Storage | Azure Blob Storage |
| **State Locking** | ✅ Enabled | ✅ Enabled |
| **Automation** | ✅ Full automation | ❌ Manual execution |
| **Use Case** | Production, team workflows | Development, testing |
| **Approval Workflow** | ✅ Built-in | ❌ Manual only |
| **Audit Trail** | ✅ GitHub Actions history | ❌ Manual tracking |
| **Security** | ✅ No credentials in repo | ⚠️ Relies on user account |

### When to Use Each Method

**Use CI/CD Deployment When**:
- Deploying to production environments
- Working in a team with multiple contributors
- Requiring approval workflows for changes
- Needing consistent, repeatable deployments
- Implementing infrastructure governance policies
- Managing multiple environments (dev, staging, prod)

**Use Manual CLI Deployment When**:
- Developing and testing Terraform configurations locally
- Learning the infrastructure setup
- Troubleshooting deployment issues
- Quick prototyping or experimentation
- Lacking permissions to create service principals
- Working in personal development environments

## State Management

### Terraform Remote State

- **Backend**: Azure Blob Storage (used by both CI/CD and manual CLI deployments)
- **Encryption**: Microsoft-managed keys (AES-256)
- **Locking**: Blob lease mechanism for concurrent operation prevention
- **Versioning**: Blob versioning enabled for state history and rollback capability

**Backend Configuration** (terraform/backend.tf):
```hcl
terraform {
  backend "azurerm" {
    # Configuration provided via:
    # - CI/CD: Environment variables (ARM_*)
    # - Manual: backend.local.hcl file
    #
    # Authentication method controlled by ARM_USE_OIDC:
    # - CI/CD: ARM_USE_OIDC=true (OIDC workload identity)
    # - Manual: Not set (Azure CLI authentication - default)
  }
}
```

### Authentication Methods for State Access

**CI/CD (OIDC)**:
```bash
# Environment variables set by GitHub Actions
ARM_USE_OIDC=true
ARM_CLIENT_ID=<service-principal-client-id>
ARM_TENANT_ID=<azure-tenant-id>
ARM_SUBSCRIPTION_ID=<azure-subscription-id>
ARM_RESOURCE_GROUP_NAME=tfstate-rg
ARM_STORAGE_ACCOUNT_NAME=tfstatexxx
ARM_CONTAINER_NAME=tfstate
ARM_KEY=dev/terraform.tfstate
```

**Manual CLI (Azure CLI)**:
```hcl
# backend.local.hcl file
resource_group_name  = "tfstate-rg"
storage_account_name = "tfstatexxx"
container_name       = "tfstate"
key                  = "dev/terraform.tfstate"
# use_oidc not set - defaults to Azure CLI auth
```

### State Security

- **Access Control**: Azure RBAC on storage account
  - CI/CD: Service principal with "Storage Blob Data Owner" role
  - Manual: User account with "Storage Blob Data Owner" role
- **Network Security**: HTTPS-only access enforced, optional private endpoint
- **Encryption**: AES-256 encryption at rest (Microsoft-managed keys)
- **Backup**: Soft delete enabled (30-day retention) and blob versioning
- **State Locking**: Prevents concurrent modifications via Azure Blob lease mechanism

## Automation Pipeline

### GitHub Actions Workflows

#### terraform-plan.yml

**Trigger**: Pull requests to main branch

**Steps**:
1. Checkout code
2. Authenticate to Azure (workload identity)
3. Initialize Terraform
4. Format validation
5. Syntax validation
6. Security scanning (checkov)
7. Generate and comment plan on PR

#### terraform-apply.yml

**Trigger**: Push to main branch (after PR merge)

**Steps**:
1. Checkout code
2. Authenticate to Azure (workload identity)
3. Initialize Terraform
4. Apply infrastructure changes
5. Output deployment details
6. Update deployment status

#### terraform-destroy.yml

**Trigger**: Manual workflow dispatch

**Steps**:
1. Manual approval required
2. Authenticate to Azure
3. Initialize Terraform
4. Destroy infrastructure
5. Confirm destruction

### Workload Identity Federation

- **No Secrets**: No service principal secrets in GitHub
- **OIDC**: GitHub OIDC token exchange with Azure
- **Short-lived Tokens**: Tokens valid only during workflow
- **Least Privilege**: Minimal permissions required

**Benefits**:
- Enhanced security (no long-lived credentials)
- Simplified secret management
- Automatic token rotation
- Audit trail in Azure AD

## Infrastructure Modules

### Module Organization

All infrastructure is organized into reusable Terraform modules:

- `azure-hub-vnet`: Hub VNET and subnets
- `azure-spoke-vnet`: Spoke VNET and peering
- `azure-load-balancer`: Internal load balancer for NVA
- `f5-xc-registration`: F5 XC site token generation
- `f5-xc-ce-appstack`: CE AppStack deployment
- `f5-xc-ce-k8s`: CE Managed Kubernetes deployment

### Module Dependencies

```
f5-xc-registration
    ↓
azure-hub-vnet → azure-load-balancer → f5-xc-ce-appstack
    ↓
azure-spoke-vnet → f5-xc-ce-k8s
```

## Scalability Considerations

### Horizontal Scaling

- **CE AppStack**: Scale out by adding instances to load balancer
- **Spoke VNETs**: Add additional spokes with peering
- **Kubernetes**: Scale managed K8s nodes per workload needs

### Vertical Scaling

- **VM SKU**: Change to larger instance sizes as needed
- **Network Bandwidth**: Accelerated networking enabled
- **Storage**: Premium SSD for optimal performance

### Performance Optimization

- **Proximity Placement Groups**: Co-locate resources for low latency
- **Accelerated Networking**: SR-IOV for high throughput
- **Zone Distribution**: Balance across availability zones
- **Load Balancer Tuning**: Optimize hash distribution

## Monitoring and Observability

### Azure Monitor Integration

- **Metrics**: VM, network, and load balancer metrics
- **Logs**: Activity logs and diagnostic logs
- **Alerts**: Proactive alerting on thresholds
- **Dashboards**: Custom dashboards for visibility

### F5 XC Observability

- **Platform Metrics**: CE node health and performance
- **Application Metrics**: Kubernetes workload metrics
- **Security Events**: Security policy violations
- **API Analytics**: API traffic and performance

## Disaster Recovery

### Backup Strategy

- **Infrastructure**: IaC in version control
- **State Files**: Versioned in blob storage
- **Configuration**: Documented in repository
- **Secrets**: Backed up in Key Vault

### Recovery Procedures

1. **Infrastructure Loss**: Redeploy from IaC
2. **Configuration Drift**: Detect and remediate with Terraform
3. **State Loss**: Restore from blob version history
4. **Region Failure**: Deploy to alternate region (manual process)

## Cost Optimization

### Resource Sizing

- **Right-sizing**: Match VM SKU to actual workload needs
- **Reserved Instances**: Commit to 1-year or 3-year terms
- **Spot Instances**: Use for non-critical dev/test workloads
- **Auto-scaling**: Scale down during off-hours

### Cost Monitoring

- **Azure Cost Management**: Track spending by resource
- **Budget Alerts**: Set budgets and alert thresholds
- **Resource Tagging**: Tag resources for cost allocation
- **Optimization Recommendations**: Act on Azure Advisor suggestions

## Related Documentation

- [Developer Guide](development.md) - Development environment and workflows
- [Requirements](requirements.md) - System requirements and specifications
- [Quickstart Guide](../specs/001-ce-cicd-automation/quickstart.md) - Step-by-step deployment
- [Implementation Plan](../specs/001-ce-cicd-automation/plan.md) - Technical implementation details

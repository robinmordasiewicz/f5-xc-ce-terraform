# Research: F5 XC CE CI/CD Automation

**Date**: 2025-10-21
**Feature**: 001-ce-cicd-automation
**Purpose**: Technical research to resolve all NEEDS CLARIFICATION items and establish implementation patterns

## Research Objectives

1. Azure hub-and-spoke architecture with NVA best practices
2. F5 XC Customer Edge deployment and registration requirements
3. Terraform Azure provider state management patterns
4. GitHub Actions authentication to Azure (workload identity federation)
5. High availability patterns for NVA deployments

## Decision 1: Azure Hub-and-Spoke NVA Architecture Pattern

### Decision
Use **Azure Load Balancer** pattern with active/active CE deployment in hub VNET

### Rationale

Based on Microsoft Azure best practices for NVA high availability, four main patterns exist:
1. Azure Load Balancer (chosen)
2. Route Server with BGP
3. Gateway Load Balancer
4. Dynamic IP and UDR Management

**Why Azure Load Balancer was chosen:**
- Supports both active/active and active/standby configurations
- Convergence time: 10-15 seconds (acceptable for CE failover)
- Well-established pattern with broad vendor support
- Simpler than BGP Route Server (no routing protocol management)
- Better for spoke VNET routing than Gateway Load Balancer (which doesn't support East-West flows)

**Key Implementation Details:**
- Internal Load Balancer in hub VNET for CE NVA instances
- Health probes on CE management interface
- SNAT required for traffic symmetry (CE is stateful appliance)
- Backend pool with 2 CE AppStack instances for HA

### Alternatives Considered

**Route Server with BGP**: Rejected because:
- Adds complexity of BGP route management
- Limited to 8 NVA instances (not needed for this deployment)
- Requires BGP expertise for troubleshooting

**Gateway Load Balancer**: Rejected because:
- Doesn't support East-West flows between Azure VMs
- Spoke-to-spoke traffic wouldn't traverse NVA
- Our use case requires spoke-to-spoke inspection

**Dynamic IP and UDR**: Rejected because:
- Only supports active/standby (poor resource utilization)
- Worst convergence time: 1-2 minutes
- Least scalable option

### References
- https://learn.microsoft.com/en-us/azure/architecture/networking/guide/network-virtual-appliance-high-availability
- https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/hybrid-networking/hub-spoke

---

## Decision 2: Hub-and-Spoke Network Topology

### Decision
Deploy standard hub-and-spoke topology with F5 XC CE AppStack in hub as NVA

### Rationale

**Hub VNET Configuration:**
- Centralizes shared services and connectivity
- Hosts CE AppStack (Secure Mesh Site) as NVA
- Contains Azure Load Balancer for CE HA
- All spoke-to-spoke traffic transits through hub NVA
- Subnet sizing: `/26` minimum for NVA subnet (as per user requirement)

**Spoke VNET Configuration:**
- Hosts CE K8s (Managed Kubernetes) workloads
- VNET peering to hub with:
  - `allow_forwarded_traffic = true` (enables hub NVA routing)
  - `allow_gateway_transit = false` (no gateway in this deployment)
  - `use_remote_gateways = false` (no VPN/ExpressRoute in MVP)
- User Defined Routes (UDR) point default route (0.0.0.0/0) to hub NVA SLI interface IP

**Key Architecture Principles:**
- One hub per region for isolation
- Non-transitive peering (spoke-to-hub only, not spoke-to-spoke directly)
- Spoke routing managed via UDR pointing to NVA
- NSGs for security enforcement at subnet level

### Implementation Details

**Hub VNET Subnets:**
- NVA Subnet: 10.0.1.0/26 (supports up to 59 usable IPs for CE instances and load balancer)
- Management Subnet: 10.0.2.0/24 (for operational access)

**Spoke VNET Subnets:**
- Workload Subnet: 10.1.1.0/24 (CE K8s cluster and application pods)
- Service Subnet: 10.1.2.0/24 (Azure services integration)

**Routing Configuration:**
- Spoke route table with UDR: 0.0.0.0/0 → Hub NVA SLI IP (e.g., 10.0.1.4)
- Hub NVA configured as next-hop for all spoke egress traffic
- CE SLI interface in hub NVA subnet receives spoke traffic

### Alternatives Considered

**Direct Spoke Peering**: Rejected because:
- User requirement specifies hub-and-spoke with NVA transit
- Doesn't provide centralized inspection/security enforcement
- Violates hub-and-spoke design principle

**Azure Firewall as NVA**: Rejected because:
- User specifically requested F5 XC CE as the NVA
- Different capabilities (F5 XC provides service mesh, not just firewall)

### References
- https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/hybrid-networking/hub-spoke
- User requirement: "hub and spoke architecture where the CE appstack instance running as a secure mesh node should be the deployed as the NVA in a Hub VNET"

---

## Decision 3: F5 XC CE Deployment and Registration

### Decision
Use F5 XC Provider for Terraform to create CE site and register automatically

### Rationale

**F5 XC CE Deployment Requirements:**
- Minimum per node: 8 vCPUs, 32 GB RAM, 80 GB disk
- Requires Azure VM with multiple NICs (SLI, SLO, management interfaces)
- Must use F5 XC CE image from Azure Marketplace
- Cloud-init used for zero-touch provisioning with registration token

**Registration Process:**
1. Create CE site in F5 XC Console (generates registration token)
2. Deploy Azure VM with cloud-init containing token
3. CE instance boots and reads token from /etc/vpm/user_data
4. CE automatically registers with F5 XC Global Controller
5. Registration confirmed when CE shows "online" status in console

**Implementation Approach:**
- Use `volterra` Terraform provider to create CE site and get registration token
- Use `azurerm` provider to deploy Azure VM with CE image
- Pass registration token via cloud-init user_data
- Wait for registration confirmation before proceeding (using Terraform provisioner or API check)

**CE Flavors:**
- **Hub NVA**: CE AppStack (Secure Mesh Site v2) - provides Layer 3/4 networking, service mesh
- **Spoke**: CE K8s (Managed Kubernetes) - provides Kubernetes cluster management

### Key Configuration Elements

**CE Site Creation (F5 XC Console):**
```hcl
resource "volterra_azure_vnet_site" "hub_ce" {
  name      = "hub-ce-site"
  namespace = "system"

  azure_region = var.azure_region
  resource_group = azurerm_resource_group.hub.name

  # Generate token for registration
  # Token stored in Terraform state, injected into cloud-init
}
```

**Azure VM Deployment:**
```hcl
resource "azurerm_virtual_machine" "ce_appstack" {
  # Use F5 XC CE image from marketplace
  # 3 NICs: SLI (inside), SLO (outside), management
  # Cloud-init with registration token

  custom_data = base64encode(templatefile("cloud-init.yaml", {
    token = volterra_azure_vnet_site.hub_ce.registration_token
  }))
}
```

**Registration Verification:**
- Poll F5 XC API for site status
- Wait until status = "online"
- Terraform provisioner or external data source for verification

### Alternatives Considered

**Manual Registration**: Rejected because:
- Violates automation requirement (zero manual steps)
- Doesn't scale for multiple CE deployments
- Error-prone and time-consuming

**Azure Marketplace Deploy**: Rejected because:
- User requirement specifies Terraform-driven deployment
- Less control over networking configuration
- Difficult to integrate into GitOps workflow

### References
- https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/reference/ce-reg-upg-ref
- https://docs.cloud.f5.com/docs-v2/multi-cloud-network-connect/how-to/site-management/deploy-sms-az-clickops
- https://azuremarketplace.microsoft.com/en-us/marketplace/apps/f5-networks.f5xc_customer_edge

---

## Decision 4: Terraform State Management

### Decision
Use Azure Blob Storage as remote backend with encryption and state locking

### Rationale

**Azure Blob Storage Backend Benefits:**
- Native integration with Azure (same cloud as infrastructure)
- State locking via lease mechanism (prevents concurrent modifications)
- Server-side encryption (SSE) with Azure-managed keys
- Versioning enabled for state history and rollback
- Soft delete protection against accidental deletion
- RBAC integration with Azure AD

**Security Configuration:**
- Storage account with private endpoint (no public access)
- Encryption at rest (Azure SSE)
- Encryption in transit (HTTPS only)
- State file contains sensitive data (passwords, tokens) - never commit to Git
- Access restricted to GitHub Actions service principal via RBAC

**Backend Configuration:**
```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatexcce"
    container_name       = "tfstate"
    key                  = "001-ce-cicd-automation.tfstate"
    use_oidc            = true  # GitHub workload identity federation
  }
}
```

### Best Practices Implemented

1. **Separate Storage Account**: Dedicated RG and storage account for Terraform state
2. **State Locking**: Blob lease mechanism prevents concurrent apply operations
3. **Versioning**: Enabled on blob container for state history
4. **Encryption**: SSE with Azure-managed keys (option for customer-managed keys)
5. **Access Control**: RBAC roles limiting access to CI/CD pipeline only
6. **Network Security**: Private endpoint, firewall rules restricting access

### Alternatives Considered

**Terraform Cloud**: Rejected because:
- Adds external dependency and cost
- Azure Blob Storage more integrated with Azure deployments
- Organization may prefer self-hosted solution

**Local State**: Rejected because:
- Cannot be used in CI/CD pipeline (no shared state)
- No state locking (corruption risk)
- No versioning or backup

**S3 Backend**: Rejected because:
- Cross-cloud dependency (Azure infra with AWS state)
- Additional authentication complexity
- Higher latency for Azure deployments

### References
- https://learn.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage
- https://developer.hashicorp.com/terraform/tutorials/azure-get-started/azure-remote
- https://techcommunity.microsoft.com/blog/fasttrackforazureblog/securing-terraform-state-in-azure/3787254

---

## Decision 5: GitHub Actions Authentication to Azure

### Decision
Use Workload Identity Federation (OIDC) with Azure AD instead of service principal secrets

### Rationale

**Workload Identity Federation Benefits:**
- **No secrets to manage**: Eliminates long-lived credentials in GitHub secrets
- **Short-lived tokens**: GitHub generates OIDC token, exchanges for Azure access token
- **Better security**: No credential leakage risk, tokens expire quickly
- **Compliance**: Meets zero-trust security requirements
- **Microsoft recommendation**: Official best practice for GitHub Actions → Azure

**How It Works:**
1. Create Azure AD application registration
2. Configure federated credential trust with GitHub (repository, branch, environment)
3. GitHub Actions generates OIDC token with claims (repo, branch, SHA)
4. Azure AD validates token and issues access token
5. Terraform uses access token to authenticate Azure provider

**GitHub Secrets Required (NOT credentials):**
- `AZURE_CLIENT_ID`: Application (client) ID
- `AZURE_TENANT_ID`: Azure AD tenant ID
- `AZURE_SUBSCRIPTION_ID`: Target subscription ID
- `F5_XC_API_TOKEN`: F5 XC Console API token (only secret, stored encrypted)

**GitHub Actions Workflow Configuration:**
```yaml
permissions:
  id-token: write  # Required for OIDC token
  contents: read

steps:
  - name: Azure Login
    uses: azure/login@v1
    with:
      client-id: ${{ secrets.AZURE_CLIENT_ID }}
      tenant-id: ${{ secrets.AZURE_TENANT_ID }}
      subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

  - name: Terraform Init
    run: terraform init
    env:
      ARM_USE_OIDC: true
      ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
      ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
      ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

### Setup Steps

1. **Azure AD Configuration:**
   - Create app registration: `az ad app create --display-name "GitHub-Actions-XC-CE"`
   - Create service principal: `az ad sp create --id <app-id>`
   - Assign RBAC roles: `az role assignment create --role Contributor --scope /subscriptions/<subscription-id>`

2. **Federated Credential:**
   ```bash
   az ad app federated-credential create \
     --id <app-id> \
     --parameters '{
       "name": "github-actions-main",
       "issuer": "https://token.actions.githubusercontent.com",
       "subject": "repo:<org>/<repo>:ref:refs/heads/main",
       "audiences": ["api://AzureADTokenExchange"]
     }'
   ```

3. **GitHub Secrets:**
   - Add `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
   - Add `F5_XC_API_TOKEN` for F5 XC provider authentication

### Alternatives Considered

**Service Principal with Secret**: Rejected because:
- Requires storing long-lived credentials in GitHub secrets
- Higher risk of credential compromise
- Secret rotation operational burden
- Not zero-trust compliant

**Managed Identity**: Rejected because:
- Only works for Azure-hosted runners (not GitHub-hosted)
- Would require self-hosted runner infrastructure

### References
- https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure
- https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect
- https://mattias.engineer/blog/2024/azure-federated-credentials-github/

---

## Decision 6: Terraform Module Structure

### Decision
Create 6 reusable Terraform modules with clear separation of concerns

### Rationale

**Module Breakdown:**

1. **azure-hub-vnet**: Hub virtual network with subnets for NVA, management
2. **azure-spoke-vnet**: Spoke virtual network with UDR routing to hub
3. **azure-load-balancer**: Internal LB for CE NVA high availability
4. **f5-xc-ce-appstack**: CE Secure Mesh Site deployment (hub NVA)
5. **f5-xc-ce-k8s**: CE Managed Kubernetes deployment (spoke)
6. **f5-xc-registration**: CE site creation and registration with F5 XC Console

**Module Design Principles:**
- Single responsibility (each module does one thing)
- Reusability across environments (dev, prod)
- Clear inputs/outputs with validation
- Self-contained with README and examples
- No hard-coded values (everything parameterized)

**Benefits:**
- DRY (Don't Repeat Yourself) - modules used in multiple environments
- Testable in isolation
- Easier to maintain and update
- Clear dependencies between modules
- Enables parallel development

### Module Dependencies

```
f5-xc-registration
  └─> f5-xc-ce-appstack (depends on token from registration)
      └─> azure-hub-vnet
      └─> azure-load-balancer

f5-xc-ce-k8s
  └─> azure-spoke-vnet
      └─> azure-hub-vnet (peering dependency)
```

### Alternatives Considered

**Monolithic Terraform**: Rejected because:
- Difficult to test individual components
- No reusability across environments
- Changes to one component affect entire deployment
- Harder to review and understand

**Too Many Modules**: Rejected because:
- Over-engineering for this use case
- Unnecessary complexity
- Increased Terraform state management overhead

### References
- https://developer.hashicorp.com/terraform/language/modules/develop
- https://www.terraform.io/docs/language/modules/develop/structure.html

---

## Implementation Checklist

- [x] Azure hub-and-spoke NVA pattern determined (Load Balancer)
- [x] Hub-and-spoke topology defined (subnet sizing, routing)
- [x] F5 XC CE deployment approach established (Terraform provider + cloud-init)
- [x] Terraform state management configured (Azure Blob Storage with encryption)
- [x] GitHub Actions authentication method selected (OIDC workload identity federation)
- [x] Terraform module structure defined (6 modules with clear separation)

## Next Steps

Proceed to Phase 1: Design & Contracts
- Create data-model.md with infrastructure entities
- Generate contracts/ directory with F5 XC API specifications
- Create quickstart.md deployment guide
- Update agent context with technology decisions

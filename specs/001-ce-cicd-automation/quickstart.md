# Quickstart: F5 XC CE CI/CD Automation Deployment

**Date**: 2025-10-21
**Feature**: 001-ce-cicd-automation
**Estimated Time**: 60-90 minutes (first-time setup)

## Overview

This quickstart guide walks you through deploying F5 Distributed Cloud Customer Edge (CE) in Azure using Terraform and GitHub Actions. The deployment creates a hub-and-spoke network topology with CE AppStack as NVA in the hub and CE Managed Kubernetes in the spoke.

**What You'll Deploy:**
- 1 Hub VNET with 2 CE AppStack instances (HA) behind Azure Load Balancer
- 1 Spoke VNET with 1 CE Managed Kubernetes instance
- Automated CI/CD pipeline for infrastructure changes
- Complete GitOps workflow for infrastructure lifecycle

**Prerequisites:**
- Azure subscription with Contributor access
- F5 Distributed Cloud account with API access
- GitHub account with repository access
- Azure CLI installed locally
- Terraform 1.6+ installed locally (for initial setup)

---

## Phase 1: Azure Setup (15-20 minutes)

### Step 1.1: Create Azure Resources for Terraform State

```bash
# Set variables
RESOURCE_GROUP="terraform-state-rg"
STORAGE_ACCOUNT="tfstatexcce$(date +%s)"  # Must be globally unique
CONTAINER_NAME="tfstate"
LOCATION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --encryption-services blob \
  --https-only true \
  --min-tls-version TLS1_2

# Create blob container
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT

# Enable versioning
az storage account blob-service-properties update \
  --account-name $STORAGE_ACCOUNT \
  --enable-versioning true
```

**Save these values** - you'll need them later:
```
STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT
CONTAINER_NAME=$CONTAINER_NAME
RESOURCE_GROUP_NAME=$RESOURCE_GROUP
```

### Step 1.2: Create Azure AD App Registration for GitHub Actions

```bash
# Create app registration
APP_NAME="GitHub-Actions-XC-CE"
az ad app create --display-name $APP_NAME

# Get application ID
APP_ID=$(az ad app list --display-name $APP_NAME --query [0].appId -o tsv)

# Create service principal
az ad sp create --id $APP_ID

# Get tenant and subscription IDs
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Assign Contributor role at subscription level
az role assignment create \
  --role Contributor \
  --assignee $APP_ID \
  --scope /subscriptions/$SUBSCRIPTION_ID

echo "Save these values for GitHub Secrets:"
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
```

### Step 1.3: Configure Federated Credentials for GitHub

```bash
# Replace with your GitHub org and repo
GITHUB_ORG="your-github-org"
GITHUB_REPO="f5-xc-ce-terraform"

# Create federated credential for main branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$GITHUB_ORG'/'$GITHUB_REPO':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated credential for pull requests
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-actions-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$GITHUB_ORG'/'$GITHUB_REPO':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

---

## Phase 2: F5 XC Console Setup (10-15 minutes)

### Step 2.1: Get F5 XC API Token

1. Log in to F5 XC Console: https://your-tenant.console.ves.volterra.io
2. Navigate to **Administration → Personal Management → Credentials**
3. Click **Add Credentials**
4. Select **API Token**
5. Name: `terraform-automation`
6. Expiration: 90 days (or as per your policy)
7. Click **Generate** and **Copy** the token immediately (won't be shown again)

**Save this value**:
```
F5_XC_API_TOKEN=<your-token-here>
```

### Step 2.2: Verify F5 XC Tenant Information

```bash
# Note your tenant name from the console URL
# Example: https://acme-corp.console.ves.volterra.io
# Tenant name: acme-corp

F5_XC_TENANT="your-tenant-name"
```

---

## Phase 3: GitHub Repository Setup (10-15 minutes)

### Step 3.1: Fork or Clone Repository

```bash
# Clone the repository
git clone https://github.com/$GITHUB_ORG/f5-xc-ce-terraform.git
cd f5-xc-ce-terraform

# Checkout feature branch
git checkout 001-ce-cicd-automation
```

### Step 3.2: Configure GitHub Secrets

Navigate to your repository on GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `AZURE_CLIENT_ID` | Application ID | From Step 1.2 |
| `AZURE_TENANT_ID` | Tenant ID | From Step 1.2 |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID | From Step 1.2 |
| `F5_XC_API_TOKEN` | API Token | From Step 2.1 |
| `F5_XC_TENANT` | Tenant Name | From Step 2.2 |
| `TF_STATE_RESOURCE_GROUP` | Resource Group | From Step 1.1 |
| `TF_STATE_STORAGE_ACCOUNT` | Storage Account | From Step 1.1 |
| `TF_STATE_CONTAINER` | Container Name | From Step 1.1 (tfstate) |

### Step 3.3: Configure Repository Variables

**Settings → Secrets and variables → Actions → Variables tab → New repository variable**

Add the following variables:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `AZURE_LOCATION` | `eastus` | Azure region for deployment |
| `HUB_VNET_NAME` | `hub-vnet` | Hub VNET name |
| `SPOKE_VNET_NAME` | `spoke-vnet` | Spoke VNET name |
| `CE_SITE_NAME_HUB` | `hub-ce-site` | F5 XC site name for hub |
| `CE_SITE_NAME_SPOKE` | `spoke-ce-site` | F5 XC site name for spoke |

---

## Phase 4: Infrastructure Configuration (15-20 minutes)

### Step 4.1: Configure Terraform Backend

Edit `terraform/backend.tf`:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"          # From Step 1.1
    storage_account_name = "tfstatexcce1234567890"       # From Step 1.1
    container_name       = "tfstate"                     # From Step 1.1
    key                  = "001-ce-cicd-automation.tfstate"
    use_oidc            = true
  }
}
```

### Step 4.2: Configure Environment Variables

Edit `terraform/environments/dev/terraform.tfvars`:

```hcl
# Azure Configuration
azure_location = "eastus"
resource_group_name = "xc-ce-dev-rg"

# Hub VNET Configuration
hub_vnet_name = "hub-vnet"
hub_address_space = ["10.0.0.0/16"]
hub_nva_subnet_prefix = "10.0.1.0/26"
hub_mgmt_subnet_prefix = "10.0.2.0/24"

# Spoke VNET Configuration
spoke_vnet_name = "spoke-vnet"
spoke_address_space = ["10.1.0.0/16"]
spoke_workload_subnet_prefix = "10.1.1.0/24"
spoke_service_subnet_prefix = "10.1.2.0/27"

# CE Configuration
ce_site_size = "medium"
ce_os_disk_size_gb = 80
ce_admin_password = "ComplexP@ssw0rd123!"  # Change this!

# F5 XC Configuration
f5_xc_tenant = "your-tenant-name"           # From Step 2.2
hub_ce_site_name = "hub-ce-site"
spoke_ce_site_name = "spoke-ce-site"

# Common Tags
common_tags = {
  environment  = "dev"
  managed_by   = "terraform"
  project      = "f5-xc-ce-automation"
  cost_center  = "infrastructure"
}
```

### Step 4.3: Validate Configuration Locally (Optional)

```bash
cd terraform/environments/dev

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Format configuration
terraform fmt -recursive

# Check what will be created
terraform plan
```

---

## Phase 5: Initial Deployment via GitHub Actions (20-30 minutes)

### Step 5.1: Create GitHub Issue

1. Go to **Issues → New Issue**
2. Title: `Initial deployment of F5 XC CE hub-and-spoke architecture`
3. Description:
   ```
   Deploy initial infrastructure:
   - Hub VNET with 2 CE AppStack instances (HA)
   - Spoke VNET with 1 CE Managed Kubernetes instance
   - Azure Load Balancer for NVA HA
   - VNET peering and routing configuration
   ```
4. Labels: `enhancement`, `infrastructure`
5. Click **Submit new issue**
6. **Note the issue number** (e.g., #1)

### Step 5.2: Commit Configuration Changes

```bash
# Ensure you're on the feature branch
git checkout 001-ce-cicd-automation

# Add your changes
git add terraform/backend.tf terraform/environments/dev/terraform.tfvars

# Commit with reference to issue
git commit -m "Configure Terraform backend and dev environment

Refs #1
- Set Azure Blob Storage backend for state
- Configure hub-and-spoke network parameters
- Set CE instance sizing and F5 XC tenant"

# Push to GitHub
git push origin 001-ce-cicd-automation
```

### Step 5.3: Create Pull Request

1. Go to GitHub repository → **Pull requests → New pull request**
2. Base: `main` ← Compare: `001-ce-cicd-automation`
3. Title: `Fixes #1: Initial F5 XC CE hub-and-spoke deployment`
4. Description:
   ```markdown
   ## Changes
   - Configured Terraform backend with Azure Blob Storage
   - Defined hub-and-spoke network topology
   - Set CE instance parameters for dev environment

   ## Testing
   - [ ] Terraform validate passed
   - [ ] Terraform plan shows expected resources
   - [ ] All GitHub Actions checks passed

   ## Deployment Impact
   - Creates new Azure resource groups
   - Deploys hub VNET (10.0.0.0/16)
   - Deploys spoke VNET (10.1.0.0/16)
   - Provisions 3 CE instances (2 hub, 1 spoke)
   - Estimated cost: $XX/month

   Fixes #1
   ```
5. Click **Create pull request**

### Step 5.4: Monitor GitHub Actions Workflow

The `terraform-plan.yml` workflow will automatically run:

1. Go to **Actions** tab
2. Click on the running workflow
3. Monitor steps:
   - ✅ Checkout code
   - ✅ Azure login (OIDC)
   - ✅ Terraform init
   - ✅ Terraform validate
   - ✅ Terraform plan
   - ✅ Post plan as PR comment

**Review the plan output** in the PR comments to verify expected resources.

### Step 5.5: Approve and Merge Pull Request

1. Review the Terraform plan output
2. Verify all resources are correct
3. Get approval from team member (if required)
4. Click **Merge pull request**
5. Click **Confirm merge**

### Step 5.6: Monitor Deployment

The `terraform-apply.yml` workflow will automatically run on main branch:

1. Go to **Actions** tab
2. Click on the running workflow
3. Monitor deployment progress (~15-20 minutes):
   - ✅ Hub VNET creation (2-3 min)
   - ✅ Spoke VNET creation (2-3 min)
   - ✅ VNET peering establishment (1 min)
   - ✅ F5 XC site registration (1 min)
   - ✅ CE VM deployment (5-7 min)
   - ✅ CE registration with F5 XC Console (3-5 min)
   - ✅ Load balancer configuration (2-3 min)

---

## Phase 6: Validation (10-15 minutes)

### Step 6.1: Verify Azure Resources

```bash
# List resource groups
az group list --query "[?tags.project=='f5-xc-ce-automation'].name" -o table

# Verify hub VNET
az network vnet show \
  --name hub-vnet \
  --resource-group xc-ce-dev-rg \
  --query "{Name:name, AddressSpace:addressSpace.addressPrefixes}" -o table

# Verify spoke VNET
az network vnet show \
  --name spoke-vnet \
  --resource-group xc-ce-dev-rg \
  --query "{Name:name, AddressSpace:addressSpace.addressPrefixes}" -o table

# Verify VNET peering
az network vnet peering list \
  --resource-group xc-ce-dev-rg \
  --vnet-name spoke-vnet \
  --query "[].{Name:name, PeeringState:peeringState}" -o table

# Verify CE VMs
az vm list \
  --resource-group xc-ce-dev-rg \
  --query "[].{Name:name, Size:hardwareProfile.vmSize, State:provisioningState}" -o table

# Verify load balancer
az network lb show \
  --name hub-nva-lb \
  --resource-group xc-ce-dev-rg \
  --query "{Name:name, FrontendIP:frontendIpConfigurations[0].privateIpAddress}" -o table
```

### Step 6.2: Verify F5 XC Console Registration

1. Log in to F5 XC Console
2. Navigate to **Multi-Cloud Network Connect → Manage → Site Management → Azure VNET Sites**
3. Verify sites are listed:
   - `hub-ce-site` - Status: **Online** (Green)
   - `spoke-ce-site` - Status: **Online** (Green)
4. Click on each site to view details:
   - Instance count
   - Last heartbeat
   - Software version
   - Health metrics (CPU, memory, disk)

### Step 6.3: Verify Network Routing

```bash
# Get hub NVA SLI IP
HUB_NVA_IP=$(az network lb frontend-ip show \
  --name hub-nva-frontend \
  --lb-name hub-nva-lb \
  --resource-group xc-ce-dev-rg \
  --query privateIpAddress -o tsv)

echo "Hub NVA SLI IP: $HUB_NVA_IP"

# Verify spoke route table
az network route-table route list \
  --route-table-name spoke-vnet-rt \
  --resource-group xc-ce-dev-rg \
  --query "[].{Name:name, AddressPrefix:addressPrefix, NextHopIP:nextHopIpAddress}" -o table

# Expected output:
# Name                 AddressPrefix    NextHopIP
# -------------------  ---------------  -----------
# default-via-hub-nva  0.0.0.0/0        10.0.1.4 (or your HUB_NVA_IP)
```

### Step 6.4: Test Connectivity (Optional)

```bash
# Deploy a test VM in spoke VNET
az vm create \
  --resource-group xc-ce-dev-rg \
  --name test-vm \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --vnet-name spoke-vnet \
  --subnet workload-subnet \
  --admin-username azureuser \
  --generate-ssh-keys

# Get test VM private IP
TEST_VM_IP=$(az vm show \
  --name test-vm \
  --resource-group xc-ce-dev-rg \
  --show-details \
  --query privateIps -o tsv)

# Verify routing through hub NVA (from within test VM)
az vm run-command invoke \
  --name test-vm \
  --resource-group xc-ce-dev-rg \
  --command-id RunShellScript \
  --scripts "traceroute -n 8.8.8.8"

# Expected: First hop should be hub NVA SLI IP
```

---

## Common Operations

### Update CE Configuration

1. Create new GitHub issue for the change
2. Create feature branch
3. Update `terraform.tfvars` with new configuration
4. Commit and push changes
5. Create pull request (triggers `terraform-plan.yml`)
6. Review plan output
7. Merge PR (triggers `terraform-apply.yml`)

### Scale CE Instances

Edit `terraform/environments/dev/terraform.tfvars`:

```hcl
# Increase hub CE instances from 2 to 3
hub_ce_instance_count = 3
```

Follow update workflow above.

### Destroy Infrastructure

**⚠️ WARNING: This will delete all resources!**

```bash
# Option 1: Via GitHub Actions (Recommended)
# Create issue for destruction
# Manually trigger terraform-destroy.yml workflow from Actions tab

# Option 2: Local destroy (if needed)
cd terraform/environments/dev
terraform destroy -auto-approve
```

---

## Troubleshooting

### Issue: CE Registration Failing

**Symptoms**: CE VM deployed but not showing "Online" in F5 XC Console

**Solutions**:
1. Verify F5 XC API token is valid and not expired
2. Check CE VM has outbound internet connectivity
3. Review cloud-init logs on CE VM:
   ```bash
   az vm run-command invoke \
     --name ce-appstack-1 \
     --resource-group xc-ce-dev-rg \
     --command-id RunShellScript \
     --scripts "cat /var/log/cloud-init-output.log"
   ```
4. Verify registration token in user_data:
   ```bash
   az vm run-command invoke \
     --name ce-appstack-1 \
     --resource-group xc-ce-dev-rg \
     --command-id RunShellScript \
     --scripts "cat /etc/vpm/user_data"
   ```

### Issue: Terraform State Lock

**Symptoms**: "Error acquiring the state lock" during Terraform operations

**Solutions**:
1. Wait 5 minutes for automatic lease expiration
2. If urgent, break lease manually:
   ```bash
   az storage blob lease break \
     --blob-name 001-ce-cicd-automation.tfstate \
     --container-name tfstate \
     --account-name $STORAGE_ACCOUNT
   ```

### Issue: GitHub Actions Authentication Failure

**Symptoms**: "AADSTS700016: Application with identifier 'xxx' was not found"

**Solutions**:
1. Verify federated credentials are configured correctly
2. Check GitHub secrets are set correctly
3. Ensure subject claim matches your repository:
   ```
   repo:<org>/<repo>:ref:refs/heads/main
   ```

### Issue: Spoke VNET Not Routing Through Hub

**Symptoms**: Traffic from spoke not traversing hub NVA

**Solutions**:
1. Verify VNET peering has `allow_forwarded_traffic = true`
2. Check route table is associated with spoke subnet
3. Verify hub NVA SLI IP is correct in route table
4. Ensure Azure Load Balancer backend pool has healthy instances

---

## Next Steps

✅ **You've successfully deployed F5 XC CE with CI/CD automation!**

**Recommended Next Steps:**

1. **Configure Applications**:
   - Deploy application workloads to spoke VNET
   - Configure F5 XC HTTP load balancers
   - Set up service mesh policies

2. **Implement Monitoring**:
   - Enable Azure Monitor for CE VMs
   - Configure F5 XC Console alerts
   - Set up log aggregation

3. **Add Environments**:
   - Create `terraform/environments/prod/` configuration
   - Set up separate GitHub environments with approvals
   - Configure production-specific networking

4. **Enhance Security**:
   - Implement Network Security Groups (NSGs)
   - Configure Azure Key Vault for secrets
   - Enable Azure Private Link for storage account

5. **Optimize Costs**:
   - Review CE instance sizing
   - Implement auto-shutdown for dev environment
   - Configure Azure Cost Management alerts

---

## Support and Resources

- **F5 XC Documentation**: https://docs.cloud.f5.com
- **Terraform Azure Provider**: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
- **GitHub Actions**: https://docs.github.com/en/actions
- **Project Issues**: https://github.com/your-org/f5-xc-ce-terraform/issues

**Estimated Monthly Costs:**
- CE VMs (3x Standard_D8s_v5): ~$800-1000
- Azure Load Balancer: ~$20-30
- VNET peering: ~$10-20
- Storage (state): <$5
- **Total**: ~$850-1100/month (dev environment)

*Costs vary by region and usage. Use Azure Pricing Calculator for precise estimates.*

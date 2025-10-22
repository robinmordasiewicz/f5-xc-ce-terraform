# Manual CLI Deployment Guide

This guide provides step-by-step instructions for deploying F5 XC Customer Edge to Azure using Terraform CLI with local Azure CLI authentication.

## Overview

Manual CLI deployment allows you to:
- Deploy directly from your local workstation without GitHub Actions
- Test infrastructure changes locally before committing
- Use Azure CLI authentication (`az login`) instead of service principals
- Maintain infrastructure state in Azure Blob Storage with state locking

## Prerequisites

### Required Software

- **Azure CLI** (2.50.0+): [Installation Guide](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Terraform** (1.6.0+): [Installation Guide](https://developer.hashicorp.com/terraform/install)
- **F5 XC Account**: Distributed Cloud Console access with API token

Verify installations:
```bash
az --version
terraform --version
```

### Required Azure Permissions

Your Azure account needs two sets of permissions:

1. **Resource Deployment**:
   - "Contributor" role on the resource group where CE nodes will be deployed
   - OR specific permissions: create/manage VMs, VNETs, NSGs, Load Balancers

2. **State Management**:
   - "Storage Blob Data Owner" role on the storage account used for Terraform state
   - Required for reading/writing state files and acquiring blob leases (state locking)

### Check Your Permissions

```bash
# Login and set subscription
az login
az account set --subscription <subscription-id>
az account show

# Check role assignments
az role assignment list --assignee <your-user-principal-id> --all
```

## Deployment Workflow

### Step 1: Azure Backend Setup

The backend setup script creates Azure Storage resources for Terraform state management.

```bash
cd f5-xc-ce-terraform
./scripts/setup-backend.sh
```

**What This Creates**:
- Resource group for Terraform state (e.g., `tfstate-rg`)
- Storage account with globally unique name (e.g., `tfstatexxx`)
- Blob container for state files (`tfstate`)
- Storage account configuration:
  - HTTPS only enforced
  - Minimum TLS version 1.2
  - Blob versioning enabled
  - Soft delete enabled (30 days)

**Script Output Example**:
```
✅ Terraform state storage account created successfully!

Backend Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resource Group:     tfstate-rg
Storage Account:    tfstatef5xcce
Container Name:     tfstate
Location:           eastus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Save these values - you'll need them for backend configuration.
```

**Important**: Save these output values. You'll use them in the next step.

### Step 2: Configure Backend

Create your backend configuration file from the template:

```bash
cd terraform/environments/dev
cp backend.local.hcl.example backend.local.hcl
```

Edit `backend.local.hcl` with your storage account details:

```hcl
# Update with values from setup-backend.sh output
resource_group_name  = "tfstate-rg"
storage_account_name = "tfstatef5xcce"
container_name       = "tfstate"
key                  = "dev/terraform.tfstate"
```

**Important Notes**:
- DO NOT add `use_oidc = true` to this file
- The backend will use Azure CLI authentication by default
- Ensure you're logged in with `az login` before terraform operations

### Step 3: Authenticate with Azure CLI

```bash
az login
```

This opens a browser for interactive authentication. After successful login:

```bash
# Set the subscription you want to deploy to
az account set --subscription <subscription-id>

# Verify you're on the correct subscription
az account show
```

**Authentication will be used for**:
- Terraform backend access (reading/writing state files)
- Azure resource deployment (creating CE nodes, networks, etc.)

### Step 4: Configure Terraform Variables

```bash
cd terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration. **Minimum required variables**:

```hcl
# F5 XC Configuration
f5_xc_tenant_name       = "your-tenant"
f5_xc_api_url           = "https://your-tenant.console.ves.volterra.io/api"

# Azure Configuration
azure_location          = "eastus"
azure_resource_group    = "f5-xc-ce-dev-rg"

# Network Configuration
hub_vnet_cidr           = "10.1.0.0/16"
spoke_vnet_cidr         = "10.2.0.0/16"
```

**F5 XC API Token**: Set as environment variable (not in tfvars for security):

```bash
export TF_VAR_f5_xc_api_token="your-xc-api-token-here"
```

**How to get F5 XC API Token**:
1. Login to F5 Distributed Cloud Console
2. Navigate to: Administration → Personal Management → Credentials
3. Click "Add Credentials"
4. Select type: "API Token"
5. Copy the generated token

### Step 5: Initialize Terraform

```bash
terraform init -backend-config=backend.local.hcl
```

**What This Does**:
- Downloads required provider plugins (Azure, F5 XC)
- Configures Azure Blob Storage as the backend
- Initializes state locking mechanism
- Creates or reads existing state file

**Expected Output**:
```
Initializing the backend...

Successfully configured the backend "azurerm"! Terraform will automatically
use this backend unless the backend configuration changes.

Initializing provider plugins...
- Finding latest version of hashicorp/azurerm...
- Finding latest version of volterraedge/volterra...

Terraform has been successfully initialized!
```

**Common Issues**:

| Error | Cause | Solution |
|-------|-------|----------|
| "storage account does not exist" | Backend not setup | Run `./scripts/setup-backend.sh` |
| "authorization failed" | Missing permissions | Add "Storage Blob Data Owner" role |
| "az login" required | Not authenticated | Run `az login` |

### Step 6: Plan Infrastructure Changes

```bash
terraform plan -out=tfplan
```

**What This Does**:
- Analyzes current infrastructure state
- Compares with desired configuration
- Shows what will be created/modified/destroyed
- Saves execution plan to `tfplan` file

**Review the Plan**:
- Verify resource counts match expectations
- Check network CIDR ranges
- Validate CE node configuration
- Ensure no unexpected deletions

**Example Output**:
```
Plan: 15 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + ce_site_name = "azure-ce-eastus"
  + hub_vnet_id  = (known after apply)
```

### Step 7: Apply Infrastructure

```bash
terraform apply tfplan
```

**What This Does**:
- Creates Azure resources according to the plan
- Registers CE nodes with F5 XC Console
- Configures network connectivity
- Updates Terraform state in Azure Storage

**Deployment Time**: Approximately 10-15 minutes

**Monitoring Progress**:
- Watch terraform output for resource creation status
- Check F5 XC Console for CE node registration
- Verify Azure Portal for resource creation

**Expected Output**:
```
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

Outputs:
ce_site_name = "azure-ce-eastus"
hub_vnet_id = "/subscriptions/.../virtualNetworks/hub-vnet"
spoke_vnet_id = "/subscriptions/.../virtualNetworks/spoke-vnet"
```

### Step 8: Verify Deployment

#### Check Terraform State

```bash
terraform state list
terraform show
```

#### Verify in Azure Portal

- Navigate to your resource group
- Confirm resources created:
  - Virtual Networks (hub and spoke)
  - CE Virtual Machines
  - Load Balancer
  - Network Security Groups
  - VNET Peering

#### Verify in F5 XC Console

- Navigate to: Multi-Cloud Network Connect → Sites
- Confirm CE site shows "Online" status
- Check site health metrics

### Step 9: Destroy Infrastructure (When Needed)

```bash
terraform destroy
```

**What This Does**:
- Removes all Azure resources created by Terraform
- De-registers CE nodes from F5 XC Console
- Updates state file to reflect deletion
- Preserves state file for historical reference

**Important**:
- Review the destroy plan carefully before confirming
- This action cannot be easily undone
- State file remains in Azure Storage for audit purposes

## Authentication Methods Comparison

### Manual CLI (Azure CLI Authentication)

| Aspect | Details |
|--------|---------|
| **Authentication** | `az login` (interactive or service principal) |
| **Setup Complexity** | Low - just install Azure CLI |
| **Prerequisites** | Azure CLI, logged-in user with required roles |
| **Backend Config** | `backend.local.hcl` file with storage account details |
| **Environment Variables** | `TF_VAR_f5_xc_api_token` |
| **Use Case** | Local development, testing, manual deployments |

### CI/CD (OIDC Workload Identity)

| Aspect | Details |
|--------|---------|
| **Authentication** | Workload identity federation (no secrets) |
| **Setup Complexity** | High - requires service principal, federated credentials, GitHub configuration |
| **Prerequisites** | Service principal with Contributor + Storage Blob Data Owner roles |
| **Backend Config** | Environment variables (`ARM_USE_OIDC=true`, `ARM_CLIENT_ID`, etc.) |
| **Environment Variables** | `ARM_USE_OIDC`, `ARM_CLIENT_ID`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`, `F5_XC_API_TOKEN` |
| **Use Case** | Automated CI/CD pipeline, production deployments |

## Environment Variables Reference

### Required for All Deployments

```bash
# F5 XC API Token
export TF_VAR_f5_xc_api_token="your-xc-api-token"
```

### Optional for Manual CLI

```bash
# Override backend configuration (alternative to backend.local.hcl)
export ARM_RESOURCE_GROUP_NAME="tfstate-rg"
export ARM_STORAGE_ACCOUNT_NAME="tfstatef5xcce"
export ARM_CONTAINER_NAME="tfstate"
export ARM_KEY="dev/terraform.tfstate"

# Azure Subscription (if not using az account set)
export ARM_SUBSCRIPTION_ID="your-subscription-id"
```

### Required for CI/CD Only

```bash
# OIDC Authentication
export ARM_USE_OIDC="true"
export ARM_CLIENT_ID="azure-app-client-id"
export ARM_TENANT_ID="azure-tenant-id"
export ARM_SUBSCRIPTION_ID="azure-subscription-id"
```

## Troubleshooting

### Authentication Issues

#### "Error: Unable to list storage account keys"

**Cause**: Missing "Storage Blob Data Owner" role on storage account

**Solution**:
```bash
# Get your user principal ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Assign role
az role assignment create \
  --role "Storage Blob Data Owner" \
  --assignee $USER_ID \
  --scope "/subscriptions/<subscription-id>/resourceGroups/tfstate-rg/providers/Microsoft.Storage/storageAccounts/tfstatef5xcce"
```

#### "Error: Failed to get existing workspaces: containers.Client#ListBlobs"

**Cause**: Not logged in with Azure CLI

**Solution**:
```bash
az login
az account set --subscription <subscription-id>
terraform init -backend-config=backend.local.hcl
```

### Backend Issues

#### "Error: Backend configuration changed"

**Cause**: Backend configuration in `backend.local.hcl` doesn't match existing state

**Solution**:
```bash
# Reconfigure backend
terraform init -reconfigure -backend-config=backend.local.hcl
```

#### "Error: Error acquiring the state lock"

**Cause**: Previous terraform operation didn't complete cleanly, leaving a lock

**Solution**:
```bash
# Check if any terraform processes are running
ps aux | grep terraform

# If none running, force unlock (use lock ID from error message)
terraform force-unlock <lock-id>
```

### Permission Issues

#### "Error: authorization failed when writing to storage account"

**Cause**: Missing "Storage Blob Data Owner" role

**Solution**: Assign role as shown in Authentication Issues section above

#### "Error: insufficient permissions to deploy resources"

**Cause**: Missing "Contributor" role on resource group

**Solution**:
```bash
az role assignment create \
  --role "Contributor" \
  --assignee <user-principal-id> \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group-name>"
```

### Common Error Messages

| Error Message | Meaning | Solution |
|--------------|---------|----------|
| "storage account not found" | Backend storage doesn't exist | Run `./scripts/setup-backend.sh` |
| "authorization failed" | Missing Azure permissions | Check role assignments |
| "provider version constraint" | Terraform version mismatch | Update to Terraform 1.6.0+ |
| "resource already exists" | Naming conflict | Choose different resource names |
| "API token invalid" | F5 XC token incorrect | Regenerate API token |

## Best Practices

### Security

- **Never commit sensitive files**:
  - `backend.local.hcl` (contains storage account details)
  - `terraform.tfvars` (contains configuration secrets)
  - `.terraform/` directory
  - `tfplan` files

- **Use environment variables** for sensitive values:
  ```bash
  export TF_VAR_f5_xc_api_token="token"
  # Instead of putting token in terraform.tfvars
  ```

- **Rotate credentials regularly**:
  - F5 XC API tokens
  - Azure CLI authentication

### State Management

- **Never edit state files manually**
- **Use state locking** (automatically enabled with Azure backend)
- **Keep state in remote backend** (Azure Storage) - never local
- **Enable state versioning** (configured by setup-backend.sh)

### Infrastructure Changes

- **Always run `terraform plan` first** before apply
- **Review plans carefully** - check what will be created/destroyed
- **Use workspace strategy** for multiple environments (dev, staging, prod)
- **Tag resources appropriately** for cost tracking and management

### Development Workflow

```bash
# 1. Make changes to Terraform configuration
vim terraform/environments/dev/main.tf

# 2. Format code
terraform fmt

# 3. Validate syntax
terraform validate

# 4. Plan changes
terraform plan -out=tfplan

# 5. Review plan output carefully

# 6. Apply changes
terraform apply tfplan

# 7. Verify in Azure Portal and F5 XC Console

# 8. Commit changes to version control
git add .
git commit -m "feat: add new CE node configuration"
git push
```

## Next Steps

After successful deployment:

1. **Configure F5 XC Services**:
   - Navigate to F5 XC Console
   - Configure load balancing services
   - Set up application delivery policies

2. **Network Configuration**:
   - Configure routing tables
   - Set up network security policies
   - Enable monitoring and logging

3. **Testing**:
   - Verify connectivity between hub and spoke
   - Test application delivery through CE nodes
   - Validate high availability failover

4. **Production Considerations**:
   - Set up CI/CD pipeline for automated deployments
   - Configure monitoring and alerting
   - Implement backup and disaster recovery procedures
   - Document runbooks and operational procedures

## Additional Resources

- [Architecture Details](architecture.md) - Technical architecture and design decisions
- [Development Guide](development.md) - Development environment setup
- [GitHub Actions Workflows](../.github/workflows/) - CI/CD pipeline examples
- [F5 XC Documentation](https://docs.cloud.f5.com) - F5 Distributed Cloud documentation
- [Azure Terraform Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs) - Provider documentation

## Support

- **GitHub Issues**: [Report issues](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/issues)
- **F5 XC Support**: Support portal at F5 Distributed Cloud Console
- **Azure Support**: Azure Portal support requests

# F5 Distributed Cloud Customer Edge - Azure Deployment

Automated deployment of F5 Distributed Cloud (XC) Customer Edge nodes to Microsoft Azure using Terraform with GitHub Actions CI/CD pipeline.

## Overview

Deploy F5 XC Customer Edge instances to Azure using infrastructure-as-code with fully automated CI/CD pipeline. This solution implements hub-and-spoke network architecture with CE AppStack NVA in the hub and CE Managed Kubernetes in the spoke.

**Key Features**:
- ✅ Fully automated deployment via GitHub Actions
- ✅ Hub-and-spoke network architecture with high availability
- ✅ Secure workload identity federation (no secrets)
- ✅ Encrypted remote state management

## Prerequisites

- **Azure**: Subscription with Contributor access
- **F5 XC**: Distributed Cloud account with API token
- **GitHub**: Repository with Actions enabled

## Quick Deployment

### 1. Azure Backend Setup

```bash
./scripts/setup-backend.sh
```

This creates the Azure storage account for Terraform state management.

### 2. Configure GitHub Secrets

Add these secrets in your repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Azure AD application ID for workload identity |
| `AZURE_TENANT_ID` | Your Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID |
| `F5_XC_API_TOKEN` | F5 XC Console API token |

### 3. Deploy Infrastructure

```bash
git add .
git commit -m "Deploy CE to Azure"
git push
```

GitHub Actions automatically validates and deploys your infrastructure. Monitor progress in the Actions tab.

## What Gets Deployed

- **Hub VNET**: Virtual network with CE AppStack nodes as Network Virtual Appliances
- **Spoke VNET**: Virtual network with CE Managed Kubernetes
- **Load Balancer**: Internal Azure Load Balancer for NVA high availability
- **VNET Peering**: Connectivity between hub and spoke networks
- **Network Security**: NSGs and routing for secure traffic flow

## Documentation

- **[Architecture Details](docs/architecture.md)** - Technical architecture and design
- **[Developer Guide](docs/development.md)** - Development environment and workflows
- **[Requirements](docs/requirements.md)** - System specifications and prerequisites
- **[Quickstart Guide](specs/001-ce-cicd-automation/quickstart.md)** - Detailed deployment instructions

## Support

- **Issues**: [GitHub Issues](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/issues)
- **F5 XC Documentation**: https://docs.cloud.f5.com
- **Azure Architecture**: https://learn.microsoft.com/azure/architecture/

## Contributing

See [Developer Guide](docs/development.md) for development environment setup and contribution guidelines.

---

🤖 **Infrastructure as Code** | ⚡ **Automated Deployment** | 🔒 **Secure by Default**

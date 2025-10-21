# F5 Distributed Cloud Customer Edge - Azure Deployment Automation

Automated deployment of F5 Distributed Cloud (XC) Customer Edge nodes to Microsoft Azure using Terraform with GitHub Actions CI/CD pipeline.

## Overview

This project implements infrastructure-as-code (IaC) for deploying F5 XC Customer Edge instances to Azure following hub-and-spoke network architecture:

- **Hub VNET**: CE AppStack (Secure Mesh Site) deployed as Network Virtual Appliance (NVA)
- **Spoke VNET**: CE Managed Kubernetes with routing through hub NVA
- **High Availability**: Azure Load Balancer for active/active NVA deployment
- **Automation**: GitHub Actions CI/CD pipeline with workload identity federation
- **State Management**: Azure Blob Storage with encryption and locking

## Architecture

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

## Quick Start

See **[Quickstart Guide](specs/001-ce-cicd-automation/quickstart.md)** for complete deployment instructions.

### Prerequisites

- Azure subscription with Contributor access
- F5 Distributed Cloud account with API token
- GitHub repository with Actions enabled
- Terraform >= 1.6.0 (for local development)
- Azure CLI >= 2.45.0 (for backend setup)

### Deployment Steps

1. **Azure Backend Setup**
   ```bash
   ./scripts/setup-backend.sh
   ```

2. **Configure GitHub Secrets**
   - `AZURE_CLIENT_ID`: Azure AD application ID
   - `AZURE_TENANT_ID`: Azure AD tenant ID
   - `AZURE_SUBSCRIPTION_ID`: Target Azure subscription
   - `F5_XC_API_TOKEN`: F5 XC Console API token

3. **Deploy Infrastructure**
   ```bash
   git commit -m "Deploy CE to Azure"
   git push
   # GitHub Actions automatically deploys via CI/CD pipeline
   ```

## Project Structure

```
├── .github/workflows/      # GitHub Actions CI/CD pipelines
├── terraform/
│   ├── environments/       # Dev/prod environment configurations
│   │   └── dev/
│   ├── modules/            # Reusable Terraform modules
│   │   ├── azure-hub-vnet/
│   │   ├── azure-spoke-vnet/
│   │   ├── azure-load-balancer/
│   │   ├── f5-xc-registration/
│   │   ├── f5-xc-ce-appstack/
│   │   └── f5-xc-ce-k8s/
│   └── backend.tf          # Remote state configuration
├── tests/                  # Integration tests and policies
├── scripts/                # Setup and validation scripts
├── docs/                   # Architecture diagrams and guides
└── specs/                  # Project specifications
```

## Features

- ✅ **Fully Automated Deployment**: Commit to deploy - zero manual steps
- ✅ **Hub-and-Spoke Architecture**: Azure best practices for network topology
- ✅ **High Availability**: Active/active NVA with Azure Load Balancer
- ✅ **Secure Authentication**: GitHub workload identity federation (no secrets)
- ✅ **Infrastructure as Code**: Complete Terraform implementation
- ✅ **CI/CD Pipeline**: GitHub Actions with automated testing
- ✅ **State Management**: Encrypted Azure Blob Storage with locking

## Documentation

- **[Quickstart Guide](specs/001-ce-cicd-automation/quickstart.md)** - Step-by-step deployment
- **[Implementation Plan](specs/001-ce-cicd-automation/plan.md)** - Technical architecture
- **[Research Decisions](specs/001-ce-cicd-automation/research.md)** - Architecture decisions
- **[Data Model](specs/001-ce-cicd-automation/data-model.md)** - Infrastructure entities
- **[API Contracts](specs/001-ce-cicd-automation/contracts/f5-xc-api.yaml)** - F5 XC API specification
- **[Task Breakdown](specs/001-ce-cicd-automation/tasks.md)** - Implementation tasks

## Requirements

### F5 XC Customer Edge Minimum Specs
- **CPU**: 8 vCPUs per node
- **Memory**: 32 GB RAM per node
- **Storage**: 80 GB disk per node

### Azure Resources
- **Hub VNET**: /16 address space with /26 NVA subnet
- **Spoke VNET**: /16 address space
- **Load Balancer**: Internal Azure Load Balancer for NVA HA
- **VM SKU**: Standard_D8s_v3 or equivalent

## Development

### Local Testing

```bash
# Format Terraform code
terraform fmt -recursive

# Validate configuration
terraform -chdir=terraform/environments/dev validate

# Run linters
tflint
yamllint .github/workflows/

# Run integration tests
cd tests/integration && go test -v ./...
```

### CI/CD Workflows

- **`terraform-plan.yml`**: Validates and plans changes on PR
- **`terraform-apply.yml`**: Deploys infrastructure on main branch
- **`terraform-destroy.yml`**: Decommissions infrastructure

## Support

- **Issues**: [GitHub Issues](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/issues)
- **F5 XC Documentation**: https://docs.cloud.f5.com
- **Azure Architecture**: https://learn.microsoft.com/en-us/azure/architecture/

## License

See [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

🤖 **Infrastructure as Code** | ⚡ **Automated Deployment** | 🔒 **Secure by Default**

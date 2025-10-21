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

### Developer Environment Setup

**IMPORTANT**: All developers MUST set up pre-commit hooks before contributing:

```bash
# One-time setup: Install pre-commit framework and hooks
./scripts/setup-dev-environment.sh
```

This script installs:
- Pre-commit framework
- All code quality tools (linters, formatters, security scanners)
- Git hooks for automatic validation

### Pre-commit Hooks (MANDATORY)

Pre-commit hooks validate ALL code changes **before** they enter version control. This is a **NON-NEGOTIABLE** requirement per project constitution.

#### Why Pre-commit Hooks?

- **Catch Issues Early**: Validate code before commit, not after PR
- **Consistent Quality**: All contributors use the same validation tools
- **Constitution Compliance**: Enforce code quality standards automatically
- **Fast Feedback**: Get immediate feedback on code quality issues

#### Validation Coverage

All file types are validated:

| File Type | Checks Performed |
|-----------|------------------|
| **Terraform** | Format check, syntax validation, documentation, tflint, checkov security |
| **YAML** | yamllint, syntax validation |
| **JSON** | Syntax validation, formatting check |
| **Markdown** | markdownlint, formatting check |
| **Shell** | shellcheck, shfmt format check |
| **Python** | ruff linter, black format check, mypy type checking |
| **Go** | gofmt check, golangci-lint |
| **Security** | detect-secrets, checkov scans |
| **General** | Trailing whitespace, line endings, merge conflicts, large files |

#### CRITICAL: Read-Only Validation

**Pre-commit hooks are configured in CHECK-ONLY mode:**

- ❌ Hooks **DO NOT** automatically fix problems
- ✅ Hooks **ONLY** display validation errors
- ✅ Developers **MUST** manually fix all issues
- ⚠️ Bypassing hooks is **STRICTLY FORBIDDEN**

**Examples:**
```bash
# ❌ WRONG - Auto-fixes issues (disabled)
terraform fmt file.tf

# ✅ RIGHT - Check-only mode (enabled)
terraform fmt -check file.tf  # Used by pre-commit

# ❌ FORBIDDEN - Bypassing hooks is prohibited
git commit --no-verify  # Constitution violation!
```

#### Using Pre-commit Hooks

Pre-commit hooks run **automatically** on every `git commit`:

```bash
# Normal workflow - hooks run automatically
git add terraform/main.tf
git commit -m "Add load balancer configuration"
# ↳ Pre-commit hooks validate all staged files
# ↳ If validation fails, commit is blocked
# ↳ Fix errors manually and commit again
```

**Manual execution:**
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run terraform-fmt --all-files
pre-commit run detect-secrets --all-files

# Update hook versions
pre-commit autoupdate
```

#### Fixing Validation Errors

When pre-commit blocks a commit:

1. **Read the error message carefully** - it shows which file(s) failed and why
2. **Fix the issues manually** - edit files to resolve validation errors
3. **Stage the fixes**: `git add <files>`
4. **Commit again**: `git commit`

**Example workflow:**
```bash
$ git commit -m "Add terraform config"
Check Terraform formatting.................................Failed
- hook id: terraform_fmt
- exit code: 1

terraform/main.tf
--- a/terraform/main.tf
+++ b/terraform/main.tf
@@ -5,7 +5,7 @@
 resource "azurerm_resource_group" "main" {
-  name     =    "my-rg"  # Too much whitespace
+  name     = "my-rg"
   location = "eastus"
 }

# Fix the formatting manually
$ terraform fmt terraform/main.tf
$ git add terraform/main.tf
$ git commit -m "Add terraform config"
✅ All checks passed!
```

#### Common Pre-commit Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `terraform fmt failed` | Inconsistent formatting | Run `terraform fmt <file>` |
| `yamllint failed` | YAML style violations | Check `.yamllint` rules, fix manually |
| `detect-secrets failed` | Hardcoded secrets detected | Remove secrets, use environment variables |
| `trailing-whitespace` | Lines end with whitespace | Remove trailing spaces |
| `end-of-file-fixer` | Missing newline at EOF | Add newline at end of file |
| `shellcheck failed` | Shell script issues | Fix per shellcheck suggestions |

#### Bypass Prevention

**Constitution Requirement: Bypassing pre-commit checks is STRICTLY PROHIBITED**

❌ **FORBIDDEN Actions:**
- `git commit --no-verify` - Skips all pre-commit hooks
- `SKIP=hook-name git commit` - Skips specific hooks
- Commenting out hooks in `.pre-commit-config.yaml`
- Disabling hooks in git config

✅ **Exception Process (Emergency Only):**
1. Document justification in PR description
2. Obtain technical lead approval
3. Create follow-up issue to fix violations
4. Limited to production incidents or security hotfixes

**CI/CD Enforcement:**
GitHub Actions runs **identical** validation checks to prevent bypass:
- All PRs are validated with same hooks
- Bypassed commits will fail CI/CD
- Reviewers will reject PRs attempting to bypass hooks

### Local Testing

```bash
# Pre-commit runs automatically on commit, but you can also:

# Run all pre-commit checks manually
pre-commit run --all-files

# Format Terraform code (after fixing pre-commit errors)
terraform fmt -recursive

# Validate configuration
terraform -chdir=terraform/environments/dev validate

# Run linters (these are also in pre-commit)
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

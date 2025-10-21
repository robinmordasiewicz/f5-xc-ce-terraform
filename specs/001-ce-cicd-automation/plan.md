# Implementation Plan: F5 XC CE CI/CD Automation

**Branch**: `001-ce-cicd-automation` | **Date**: 2025-10-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ce-cicd-automation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Deploy F5 Distributed Cloud Customer Edge (CE) nodes to Microsoft Azure using Terraform with GitHub Actions CI/CD pipeline. Implementation follows Azure hub-and-spoke architecture with CE AppStack (Secure Mesh Site) as NVA in hub VNET and CE K8s (Managed Kubernetes) in spoke VNET. All infrastructure is defined as code, with automated deployment, updates, and destruction through source control-driven pipeline. Authentication uses GitHub workload identity federation (no secrets), state stored in Azure Blob Storage with encryption and locking.

## Technical Context

**Language/Version**: HCL (Terraform 1.6+)
**Primary Dependencies**:
- Terraform Azure Provider (azurerm ~> 3.80)
- Terraform Azure AD Provider (azuread ~> 2.45)
- F5 XC Provider (volterra ~> 0.11)

**Storage**: Azure Blob Storage for Terraform state with encryption, versioning, and state locking via lease mechanism

**Testing**:
- Terraform validate for syntax checking
- Terraform plan for change preview
- terraform-compliance for policy-as-code validation
- Integration tests using Terratest (Go-based)
- Azure Resource validation using Azure CLI

**Target Platform**: Microsoft Azure (any region supporting F5 XC CE)

**Project Type**: Single infrastructure-as-code project with modular Terraform structure

**Performance Goals**:
- CE deployment: <15 minutes from commit to registered
- Terraform plan: <30 seconds
- Terraform apply: <10 minutes for full deployment
- Pipeline execution: <20 minutes end-to-end

**Constraints**:
- CE minimum requirements: 8 vCPUs, 32 GB RAM, 80 GB disk per node
- Hub VNET must have `/26` subnet for NVA
- Spoke VNET routing must point to Hub NVA SLI interface
- F5 XC registration requires outbound connectivity to F5 Console
- Azure Load Balancer for NVA HA (internal LB)
- State file must be encrypted and locked during operations

**Scale/Scope**:
- Initial deployment: 1 hub VNET + 1 spoke VNET
- CE nodes: 2 for HA (hub), 1 for spoke
- Terraform modules: 5-7 reusable modules
- GitHub Actions workflows: 3 (plan, apply, destroy)
- Estimated LOC: ~2000 lines (Terraform + YAML)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. GitHub Workflow Discipline ✅ COMPLIANT

- **Issue Creation**: Feature tracked as GitHub issue before implementation
- **Branch Strategy**: Working in feature branch `001-ce-cicd-automation`
- **Pull Request**: All changes will go through PR with approval
- **Issue Closure**: Will close after PR merge and validation

### II. Code Quality Standards ✅ COMPLIANT

- **Linting**:
  - `terraform fmt` for formatting (enforced in pre-commit hook)
  - `tflint` for Terraform-specific linting
  - `yamllint` for GitHub Actions workflows
- **Code Review**: PR review required with constitution checklist
- **Documentation**:
  - Module README.md with usage examples
  - Inline comments for complex networking logic
  - quickstart.md for operators
- **Security**:
  - No hardcoded credentials (using GitHub secrets + OIDC)
  - F5 XC token stored in GitHub secrets
  - Azure credentials via workload identity federation
  - Sensitive outputs marked as `sensitive = true`

### III. Testing Standards ✅ COMPLIANT

- **Tests Written First**:
  - Terraform plan tests verify expected resources
  - Integration tests validate CE registration
  - Network tests confirm routing configuration
- **Test Coverage Requirements**:
  - **Unit Tests**: Each Terraform module has test coverage
  - **Integration Tests**: Full deployment tested end-to-end
  - **Contract Tests**: F5 XC API registration verified
- **Test Quality Standards**:
  - Tests run in isolated test subscription
  - Terraform destroy in cleanup phase
  - Tests complete in <15 minutes

### IV. User Experience Consistency ✅ COMPLIANT

- **Interface Consistency**:
  - Terraform outputs provide clear deployment summary
  - Error messages include troubleshooting guidance
  - GitHub Actions logs structured by phase
- **Performance Experience**:
  - Pipeline shows progress for long operations
  - Terraform plan shows resource counts
  - Status updates at each deployment phase
- **Documentation Experience**:
  - quickstart.md with step-by-step instructions
  - Examples for common operations
  - Troubleshooting guide for errors

### V. Performance Requirements ✅ COMPLIANT

- **Response Time Standards**:
  - Terraform plan: <30s (meets <200ms API requirement N/A)
  - Pipeline execution: <20min total
  - CE deployment: <15min (meets spec SC-001)
- **Resource Efficiency**:
  - Terraform state stored remotely (no local bloat)
  - Pipeline uses caching for dependencies
  - Parallel module deployment where possible
- **Monitoring Required**:
  - GitHub Actions execution metrics
  - Terraform Cloud/Enterprise monitoring (if used)
  - Azure Monitor for deployed CE health

### Constitution Compliance Summary

**Status**: ✅ ALL GATES PASSED

No constitution violations. Project follows all core principles:
- GitHub workflow discipline enforced through branch and PR requirements
- Code quality ensured through linting, review, and documentation
- Testing standards met with TDD approach and comprehensive test coverage
- UX consistency through clear outputs and documentation
- Performance requirements within acceptable ranges for infrastructure automation

## Project Structure

### Documentation (this feature)

```
specs/001-ce-cicd-automation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── f5-xc-api.yaml  # F5 XC registration API contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Infrastructure-as-Code project structure
.
├── .github/
│   └── workflows/
│       ├── terraform-plan.yml       # PR validation workflow
│       ├── terraform-apply.yml      # Main branch deployment
│       └── terraform-destroy.yml    # Decommission workflow
│
├── terraform/
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── terraform.tfvars    # Environment-specific values
│   │   └── prod/
│   │       └── ... (same structure)
│   │
│   ├── modules/
│   │   ├── azure-hub-vnet/
│   │   │   ├── main.tf             # Hub VNET with NVA subnets
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   │
│   │   ├── azure-spoke-vnet/
│   │   │   ├── main.tf             # Spoke VNET with routing to hub
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   │
│   │   ├── f5-xc-ce-appstack/
│   │   │   ├── main.tf             # CE Secure Mesh Site (hub NVA)
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   │
│   │   ├── f5-xc-ce-k8s/
│   │   │   ├── main.tf             # CE Managed K8s (spoke)
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   │
│   │   ├── azure-load-balancer/
│   │   │   ├── main.tf             # Internal LB for NVA HA
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   │
│   │   └── f5-xc-registration/
│   │       ├── main.tf             # CE registration with F5 XC Console
│   │       ├── variables.tf
│   │       ├── outputs.tf
│   │       └── README.md
│   │
│   └── backend.tf                  # Remote state configuration
│
├── tests/
│   ├── integration/
│   │   ├── ce_registration_test.go
│   │   ├── network_routing_test.go
│   │   └── e2e_deployment_test.go
│   │
│   └── policies/
│       ├── naming_convention.rego  # terraform-compliance policies
│       └── security_groups.rego
│
├── scripts/
│   ├── setup-backend.sh            # Initialize Azure backend storage
│   ├── validate-deployment.sh      # Post-deployment validation
│   └── cleanup-orphaned-resources.sh
│
├── docs/
│   ├── architecture-diagrams/
│   │   ├── hub-spoke-topology.png
│   │   └── ce-deployment-flow.png
│   └── troubleshooting.md
│
├── .terraform.lock.hcl
├── .gitignore
└── README.md
```

**Structure Decision**: Single infrastructure-as-code project with modular Terraform layout. Chose this structure because:

1. **Modularity**: Reusable modules for hub, spoke, CE deployments enable DRY principles
2. **Environment Separation**: `environments/` directory allows dev/prod isolation with shared modules
3. **GitHub Actions Integration**: `.github/workflows/` colocated with infrastructure code for GitOps workflow
4. **Testing**: Separate `tests/` directory for integration tests and policy validation
5. **Operational Scripts**: `scripts/` for setup, validation, and maintenance tasks
6. **Documentation**: `docs/` with architecture diagrams and troubleshooting guides

This structure follows Terraform best practices for large-scale deployments while maintaining clear separation of concerns and enabling parallel development of modules.

## Complexity Tracking

*No constitution violations - table not needed*

All principles adhered to without requiring exceptions.

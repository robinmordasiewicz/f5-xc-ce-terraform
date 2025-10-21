# Tasks: F5 XC CE CI/CD Automation

**Input**: Design documents from `/specs/001-ce-cicd-automation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per constitution TDD standards. Tests must be written FIRST and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Infrastructure project**: `terraform/`, `.github/workflows/`, `tests/`, `scripts/` at repository root
- Module paths: `terraform/modules/<module-name>/`
- Environment paths: `terraform/environments/<env>/`
- All paths are from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure per plan.md layout
- [ ] T002 Initialize Terraform project with version constraints in terraform/environments/dev/versions.tf
- [ ] T003 [P] Create .gitignore file at repository root with Terraform, Azure, and secrets patterns
- [ ] T004 [P] Create README.md at repository root with project overview and quick start links
- [ ] T005 [P] Configure Terraform backend for Azure Blob Storage in terraform/backend.tf
- [ ] T006 [P] Create terraform.tfvars.example in terraform/environments/dev/ with all required variables
- [ ] T007 [P] Configure terraform fmt pre-commit hook in .git/hooks/pre-commit
- [ ] T008 [P] Create tflint configuration file .tflint.hcl at repository root
- [ ] T009 [P] Create yamllint configuration file .yamllint at repository root

**Checkpoint**: Project structure initialized - ready for foundational infrastructure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Azure Backend and CI/CD Foundation

- [ ] T010 Create Azure backend storage account setup script in scripts/setup-backend.sh
- [ ] T011 [P] Create GitHub Actions reusable workflow for Terraform init in .github/workflows/terraform-init.yml
- [ ] T012 [P] Create GitHub Actions reusable workflow for Terraform validate in .github/workflows/terraform-validate.yml
- [ ] T013 [P] Create GitHub Actions workflow for PR validation (plan) in .github/workflows/terraform-plan.yml
- [ ] T014 [P] Create GitHub Actions workflow for main branch deployment (apply) in .github/workflows/terraform-apply.yml
- [ ] T015 [P] Create GitHub Actions workflow for infrastructure destruction in .github/workflows/terraform-destroy.yml

### Terraform Module Scaffolding

- [ ] T016 [P] Create azure-hub-vnet module structure in terraform/modules/azure-hub-vnet/ with main.tf, variables.tf, outputs.tf, README.md
- [ ] T017 [P] Create azure-spoke-vnet module structure in terraform/modules/azure-spoke-vnet/ with main.tf, variables.tf, outputs.tf, README.md
- [ ] T018 [P] Create azure-load-balancer module structure in terraform/modules/azure-load-balancer/ with main.tf, variables.tf, outputs.tf, README.md
- [ ] T019 [P] Create f5-xc-registration module structure in terraform/modules/f5-xc-registration/ with main.tf, variables.tf, outputs.tf, README.md
- [ ] T020 [P] Create f5-xc-ce-appstack module structure in terraform/modules/f5-xc-ce-appstack/ with main.tf, variables.tf, outputs.tf, README.md
- [ ] T021 [P] Create f5-xc-ce-k8s module structure in terraform/modules/f5-xc-ce-k8s/ with main.tf, variables.tf, outputs.tf, README.md

### Testing Infrastructure

- [ ] T022 Create Terratest test structure in tests/integration/ with module_test.go
- [ ] T023 [P] Create terraform-compliance policy for naming conventions in tests/policies/naming_convention.rego
- [ ] T024 [P] Create terraform-compliance policy for security groups in tests/policies/security_groups.rego
- [ ] T025 [P] Create deployment validation script in scripts/validate-deployment.sh
- [ ] T026 [P] Create orphaned resources cleanup script in scripts/cleanup-orphaned-resources.sh

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Initial CE Deployment (Priority: P1) 🎯 MVP

**Goal**: Deploy F5 XC CE node to Azure with automated registration through CI/CD pipeline

**Independent Test**: Commit CE configuration to source control and verify functional CE node is deployed and registered with F5 XC Console

### Tests for User Story 1 (REQUIRED per TDD) ⚠️

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T027 [P] [US1] Create contract test for F5 XC site creation API in tests/integration/ce_site_creation_test.go
- [ ] T028 [P] [US1] Create integration test for CE registration in tests/integration/ce_registration_test.go
- [ ] T029 [P] [US1] Create integration test for network routing validation in tests/integration/network_routing_test.go
- [ ] T030 [P] [US1] Create end-to-end deployment test in tests/integration/e2e_deployment_test.go

### Implementation for User Story 1

#### Hub VNET and Networking

- [ ] T031 [P] [US1] Implement Hub VNET resource in terraform/modules/azure-hub-vnet/main.tf
- [ ] T032 [P] [US1] Implement NVA subnet resource in terraform/modules/azure-hub-vnet/main.tf
- [ ] T033 [P] [US1] Implement management subnet resource in terraform/modules/azure-hub-vnet/main.tf
- [ ] T034 [P] [US1] Define Hub VNET variables in terraform/modules/azure-hub-vnet/variables.tf
- [ ] T035 [P] [US1] Define Hub VNET outputs in terraform/modules/azure-hub-vnet/outputs.tf
- [ ] T036 [P] [US1] Create Hub VNET module README with usage examples in terraform/modules/azure-hub-vnet/README.md

#### Spoke VNET and Peering

- [ ] T037 [P] [US1] Implement Spoke VNET resource in terraform/modules/azure-spoke-vnet/main.tf
- [ ] T038 [P] [US1] Implement workload subnet resource in terraform/modules/azure-spoke-vnet/main.tf
- [ ] T039 [P] [US1] Implement service subnet resource in terraform/modules/azure-spoke-vnet/main.tf
- [ ] T040 [US1] Implement VNET peering (spoke-to-hub) in terraform/modules/azure-spoke-vnet/main.tf (depends on T031, T037)
- [ ] T041 [US1] Implement route table with UDR to hub NVA in terraform/modules/azure-spoke-vnet/main.tf (depends on T046)
- [ ] T042 [P] [US1] Define Spoke VNET variables in terraform/modules/azure-spoke-vnet/variables.tf
- [ ] T043 [P] [US1] Define Spoke VNET outputs in terraform/modules/azure-spoke-vnet/outputs.tf
- [ ] T044 [P] [US1] Create Spoke VNET module README with usage examples in terraform/modules/azure-spoke-vnet/README.md

#### Azure Load Balancer for HA

- [ ] T045 [P] [US1] Implement Internal Load Balancer resource in terraform/modules/azure-load-balancer/main.tf
- [ ] T046 [P] [US1] Implement LB frontend IP configuration in terraform/modules/azure-load-balancer/main.tf
- [ ] T047 [P] [US1] Implement LB backend address pool in terraform/modules/azure-load-balancer/main.tf
- [ ] T048 [P] [US1] Implement LB health probe for CE instances in terraform/modules/azure-load-balancer/main.tf
- [ ] T049 [P] [US1] Implement LB rules for all-ports forwarding in terraform/modules/azure-load-balancer/main.tf
- [ ] T050 [P] [US1] Define Load Balancer variables in terraform/modules/azure-load-balancer/variables.tf
- [ ] T051 [P] [US1] Define Load Balancer outputs in terraform/modules/azure-load-balancer/outputs.tf
- [ ] T052 [P] [US1] Create Load Balancer module README with usage examples in terraform/modules/azure-load-balancer/README.md

#### F5 XC Site Registration

- [ ] T053 [P] [US1] Implement F5 XC site resource for hub CE in terraform/modules/f5-xc-registration/main.tf
- [ ] T054 [P] [US1] Implement registration token output (sensitive) in terraform/modules/f5-xc-registration/outputs.tf
- [ ] T055 [P] [US1] Define F5 XC registration variables in terraform/modules/f5-xc-registration/variables.tf
- [ ] T056 [P] [US1] Create F5 XC registration module README with usage examples in terraform/modules/f5-xc-registration/README.md

#### CE AppStack Deployment (Hub NVA)

- [ ] T057 [P] [US1] Create cloud-init template for CE AppStack in terraform/modules/f5-xc-ce-appstack/cloud-init.yaml
- [ ] T058 [P] [US1] Implement network interface for SLI in terraform/modules/f5-xc-ce-appstack/main.tf
- [ ] T059 [P] [US1] Implement network interface for SLO in terraform/modules/f5-xc-ce-appstack/main.tf
- [ ] T060 [P] [US1] Implement network interface for management in terraform/modules/f5-xc-ce-appstack/main.tf
- [ ] T061 [US1] Implement CE AppStack VM resource (instance 1) in terraform/modules/f5-xc-ce-appstack/main.tf (depends on T053, T058-T060)
- [ ] T062 [US1] Implement CE AppStack VM resource (instance 2) in terraform/modules/f5-xc-ce-appstack/main.tf (depends on T053, T058-T060)
- [ ] T063 [US1] Implement backend pool association for CE instances in terraform/modules/f5-xc-ce-appstack/main.tf (depends on T047, T061-T062)
- [ ] T064 [P] [US1] Define CE AppStack variables in terraform/modules/f5-xc-ce-appstack/variables.tf
- [ ] T065 [P] [US1] Define CE AppStack outputs in terraform/modules/f5-xc-ce-appstack/outputs.tf
- [ ] T066 [P] [US1] Create CE AppStack module README with usage examples in terraform/modules/f5-xc-ce-appstack/README.md

#### CE Managed Kubernetes Deployment (Spoke)

- [ ] T067 [P] [US1] Create cloud-init template for CE K8s in terraform/modules/f5-xc-ce-k8s/cloud-init.yaml
- [ ] T068 [P] [US1] Implement network interface for K8s node in terraform/modules/f5-xc-ce-k8s/main.tf
- [ ] T069 [US1] Implement CE K8s VM resource in terraform/modules/f5-xc-ce-k8s/main.tf (depends on T053, T068)
- [ ] T070 [P] [US1] Define CE K8s variables in terraform/modules/f5-xc-ce-k8s/variables.tf
- [ ] T071 [P] [US1] Define CE K8s outputs in terraform/modules/f5-xc-ce-k8s/outputs.tf
- [ ] T072 [P] [US1] Create CE K8s module README with usage examples in terraform/modules/f5-xc-ce-k8s/README.md

#### Environment Configuration

- [ ] T073 [US1] Create dev environment main.tf in terraform/environments/dev/main.tf (orchestrates all modules)
- [ ] T074 [P] [US1] Create dev environment variables.tf in terraform/environments/dev/variables.tf
- [ ] T075 [P] [US1] Create dev environment outputs.tf in terraform/environments/dev/outputs.tf
- [ ] T076 [P] [US1] Create dev environment terraform.tfvars with sample values in terraform/environments/dev/terraform.tfvars

#### CI/CD Integration and Validation

- [ ] T077 [US1] Configure GitHub secrets for Azure and F5 XC credentials (manual step documented in quickstart.md)
- [ ] T078 [US1] Test terraform plan workflow by creating PR (manual validation)
- [ ] T079 [US1] Test terraform apply workflow by merging to main (manual validation)
- [ ] T080 [US1] Verify CE registration in F5 XC Console (manual validation per quickstart.md)
- [ ] T081 [US1] Verify network routing from spoke to hub NVA (manual validation per quickstart.md)
- [ ] T082 [US1] Run integration test suite for User Story 1 in tests/integration/

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. This is the MVP! 🎯

---

## Phase 4: User Story 2 - Configuration Updates (Priority: P2)

**Goal**: Enable safe configuration changes through source control with automated apply/recreate

**Independent Test**: Modify existing CE configuration (instance size, network settings) and verify pipeline applies changes correctly

### Tests for User Story 2 (REQUIRED per TDD) ⚠️

- [ ] T083 [P] [US2] Create test for configuration update detection in tests/integration/config_update_test.go
- [ ] T084 [P] [US2] Create test for in-place update (no recreation) in tests/integration/in_place_update_test.go
- [ ] T085 [P] [US2] Create test for resource recreation with re-registration in tests/integration/recreation_test.go

### Implementation for User Story 2

- [ ] T086 [P] [US2] Add Terraform lifecycle rules for controlled updates in terraform/modules/f5-xc-ce-appstack/main.tf
- [ ] T087 [P] [US2] Add Terraform lifecycle rules for controlled updates in terraform/modules/f5-xc-ce-k8s/main.tf
- [ ] T088 [US2] Implement graceful CE deregistration logic in terraform/modules/f5-xc-registration/main.tf
- [ ] T089 [US2] Add change detection and approval workflow to terraform-plan.yml in .github/workflows/terraform-plan.yml
- [ ] T090 [US2] Add change summary output to terraform-apply.yml in .github/workflows/terraform-apply.yml
- [ ] T091 [P] [US2] Create documentation for safe update procedures in docs/update-procedures.md
- [ ] T092 [US2] Test configuration update by changing VM size (manual validation)
- [ ] T093 [US2] Test configuration update by changing network settings (manual validation)
- [ ] T094 [US2] Verify CE maintains registration after in-place update (manual validation)
- [ ] T095 [US2] Run integration test suite for User Story 2 in tests/integration/

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Infrastructure Destruction (Priority: P3)

**Goal**: Safe decommissioning of CE deployments with complete cleanup

**Independent Test**: Mark CE configuration for deletion and verify pipeline deregisters CE and removes all resources

### Tests for User Story 3 (REQUIRED per TDD) ⚠️

- [ ] T096 [P] [US3] Create test for CE deregistration before destruction in tests/integration/deregistration_test.go
- [ ] T097 [P] [US3] Create test for complete resource cleanup in tests/integration/cleanup_test.go
- [ ] T098 [P] [US3] Create test for orphaned resource detection in tests/integration/orphan_detection_test.go

### Implementation for User Story 3

- [ ] T099 [US3] Implement pre-destroy deregistration logic in terraform/modules/f5-xc-registration/main.tf
- [ ] T100 [US3] Add destroy plan preview to terraform-destroy.yml workflow in .github/workflows/terraform-destroy.yml
- [ ] T101 [US3] Add manual approval gate for terraform-destroy.yml workflow in .github/workflows/terraform-destroy.yml
- [ ] T102 [P] [US3] Enhance cleanup script to detect orphaned resources in scripts/cleanup-orphaned-resources.sh
- [ ] T103 [P] [US3] Create destruction audit log output in terraform/environments/dev/outputs.tf
- [ ] T104 [P] [US3] Create documentation for safe destruction procedures in docs/destruction-procedures.md
- [ ] T105 [US3] Test destruction workflow by manually triggering destroy (manual validation)
- [ ] T106 [US3] Verify CE deregistered from F5 XC Console before resources deleted (manual validation)
- [ ] T107 [US3] Verify no orphaned resources in Azure after destruction (manual validation per quickstart.md)
- [ ] T108 [US3] Run integration test suite for User Story 3 in tests/integration/

**Checkpoint**: All MVP user stories (P1-P3) should now be independently functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T109 [P] Create comprehensive README.md with architecture diagrams in docs/
- [ ] T110 [P] Create troubleshooting guide in docs/troubleshooting.md
- [ ] T111 [P] Create architecture diagrams (hub-spoke topology, deployment flow) in docs/architecture-diagrams/
- [ ] T112 [P] Add cost estimation documentation in docs/cost-estimation.md
- [ ] T113 [P] Create CONTRIBUTING.md with development guidelines at repository root
- [ ] T114 Run terraform fmt on all .tf files across all modules and environments
- [ ] T115 Run tflint on all modules and fix any warnings in terraform/modules/
- [ ] T116 Run yamllint on all GitHub Actions workflows in .github/workflows/
- [ ] T117 [P] Add monitoring and alerting documentation in docs/monitoring.md
- [ ] T118 [P] Create security hardening checklist in docs/security-checklist.md
- [ ] T119 Run quickstart.md validation end-to-end (manual validation)
- [ ] T120 Create pull request template in .github/pull_request_template.md
- [ ] T121 Create issue templates for bug reports and feature requests in .github/ISSUE_TEMPLATE/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - No dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on US1 completion (requires existing deployment to update)
- **User Story 3 (Phase 5)**: Depends on US1 completion (requires existing deployment to destroy)
- **Polish (Phase N)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - COMPLETELY INDEPENDENT - This is the MVP!
- **User Story 2 (P2)**: Requires User Story 1 complete (needs existing deployment to modify)
- **User Story 3 (P3)**: Requires User Story 1 complete (needs existing deployment to destroy)
- **User Story 4 (P4)**: SKIPPED FOR MVP (multi-cloud support for future iteration)
- **User Story 5 (P5)**: SKIPPED FOR MVP (rollback feature for future iteration)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD requirement)
- Hub VNET before Spoke VNET (peering dependency)
- F5 XC registration before CE deployment (token dependency)
- CE VMs before load balancer backend association
- All infrastructure before CI/CD validation

### Parallel Opportunities

**Setup Phase (T001-T009):**
- T003-T009 can all run in parallel (different files, no dependencies)

**Foundational Phase (T010-T026):**
- T011-T015 (GitHub Actions workflows) can run in parallel
- T016-T021 (Module scaffolding) can run in parallel
- T023-T026 (Test infrastructure) can run in parallel

**User Story 1 - Tests (T027-T030):**
- All 4 tests can be written in parallel

**User Story 1 - Hub VNET (T031-T036):**
- T031-T033 (Hub VNET resources) can run in parallel
- T034-T036 (Variables, outputs, README) can run in parallel

**User Story 1 - Spoke VNET (T037-T039, T042-T044):**
- T037-T039 (Spoke VNET resources) can run in parallel
- T042-T044 (Variables, outputs, README) can run in parallel
- Sequential: T040 (peering) depends on T031+T037, T041 (UDR) depends on T046 (LB frontend IP)

**User Story 1 - Load Balancer (T045-T052):**
- T045-T049 (LB resources) can run in parallel
- T050-T052 (Variables, outputs, README) can run in parallel

**User Story 1 - F5 XC Registration (T053-T056):**
- All 4 tasks can run in parallel

**User Story 1 - CE AppStack (T057-T066):**
- T057-T060 (Cloud-init and NICs) can run in parallel
- T064-T066 (Variables, outputs, README) can run in parallel
- Sequential: T061-T062 depend on T053+T058-T060, T063 depends on T047+T061-T062

**User Story 1 - CE K8s (T067-T072):**
- T067-T068 can run in parallel
- T070-T072 (Variables, outputs, README) can run in parallel
- Sequential: T069 depends on T053+T068

**User Story 1 - Environment (T073-T076):**
- T074-T076 can run in parallel after T073

**User Story 2 - Tests (T083-T085):**
- All 3 tests can run in parallel

**User Story 2 - Implementation (T086-T091):**
- T086-T087 (lifecycle rules) can run in parallel
- T091 can run in parallel with others

**User Story 3 - Tests (T096-T098):**
- All 3 tests can run in parallel

**User Story 3 - Implementation (T102-T104):**
- T102-T104 can run in parallel

**Polish Phase (T109-T121):**
- T109-T113, T117-T118, T120-T121 can all run in parallel (documentation tasks)

---

## Parallel Example: User Story 1 - Hub VNET Module

```bash
# Launch all Hub VNET resources together:
Task: "T031 [P] [US1] Implement Hub VNET resource in terraform/modules/azure-hub-vnet/main.tf"
Task: "T032 [P] [US1] Implement NVA subnet resource in terraform/modules/azure-hub-vnet/main.tf"
Task: "T033 [P] [US1] Implement management subnet resource in terraform/modules/azure-hub-vnet/main.tf"

# Launch all Hub VNET documentation together:
Task: "T034 [P] [US1] Define Hub VNET variables in terraform/modules/azure-hub-vnet/variables.tf"
Task: "T035 [P] [US1] Define Hub VNET outputs in terraform/modules/azure-hub-vnet/outputs.tf"
Task: "T036 [P] [US1] Create Hub VNET module README with usage examples in terraform/modules/azure-hub-vnet/README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T009)
2. Complete Phase 2: Foundational (T010-T026) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T027-T082)
4. **STOP and VALIDATE**: Test User Story 1 independently using quickstart.md
5. Deploy/demo if ready

**This delivers a working, automated CE deployment system!** 🎯

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add Polish phase → Final production-ready release

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - **Developer A**: User Story 1 (Hub VNET + CE AppStack + Load Balancer modules)
   - **Developer B**: User Story 1 (Spoke VNET + CE K8s modules)
   - **Developer C**: User Story 1 (F5 XC Registration module + CI/CD workflows)
3. Stories integrate and complete independently

---

## Notes

- **[P] tasks**: Different files, no dependencies - run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **TDD**: Tests written FIRST and must FAIL before implementation (per constitution)
- **Checkpoint**: Stop at each checkpoint to validate story independently
- Each user story should be independently completable and testable
- Verify tests fail before implementing (red-green-refactor)
- Commit after each task or logical group
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Summary

**Total Tasks**: 121
**MVP Tasks (US1 only)**: 82 tasks (T001-T082)
**Full Delivery (US1-US3 + Polish)**: 121 tasks

### Task Count by Phase:
- **Phase 1 (Setup)**: 9 tasks
- **Phase 2 (Foundational)**: 17 tasks (BLOCKS all user stories)
- **Phase 3 (US1 - MVP)**: 56 tasks ⭐
- **Phase 4 (US2)**: 13 tasks
- **Phase 5 (US3)**: 13 tasks
- **Phase N (Polish)**: 13 tasks

### Parallel Opportunities Identified:
- **Setup phase**: 7 parallel tasks (T003-T009)
- **Foundational phase**: 11 parallel tasks
- **US1 tests**: 4 parallel tasks
- **US1 Hub VNET**: 6 parallel tasks
- **US1 Spoke VNET**: 6 parallel tasks (with 2 sequential)
- **US1 Load Balancer**: 8 parallel tasks
- **US1 F5 XC Registration**: 4 parallel tasks
- **US1 CE AppStack**: 8 parallel tasks (with 3 sequential)
- **US1 CE K8s**: 5 parallel tasks (with 1 sequential)
- **US2 tasks**: 6 parallel tasks
- **US3 tasks**: 6 parallel tasks
- **Polish tasks**: 9 parallel tasks

**Total parallel opportunities**: ~80 tasks can be parallelized with proper team coordination

### Independent Test Criteria:

**User Story 1 (P1 - MVP)**:
- ✅ Commit CE config → Pipeline deploys → CE registered "online" in F5 XC Console
- ✅ Spoke VNET routes through hub NVA SLI
- ✅ All tests in tests/integration/ pass
- ✅ Quickstart.md validation passes

**User Story 2 (P2)**:
- ✅ Modify config (VM size) → Pipeline shows plan → Apply updates only affected resources
- ✅ CE maintains registration after update
- ✅ Change requiring recreation → Old CE deregistered → New CE registered

**User Story 3 (P3)**:
- ✅ Mark for deletion → Pipeline deregisters CE → Destroys all resources
- ✅ No orphaned resources in Azure
- ✅ Complete audit trail in logs

### Suggested MVP Scope:

**Minimum Viable Product = User Story 1 (P1) ONLY**
- Tasks: T001-T082 (82 tasks)
- Estimated effort: 2-3 weeks for solo developer, 1 week for 3-person team
- Delivers: Fully automated CE deployment with hub-and-spoke architecture, CI/CD pipeline, and F5 XC registration
- Value: Eliminates manual CE deployment, provides GitOps workflow, enables infrastructure-as-code

**After MVP validation, add**:
- User Story 2 (P2): Configuration updates (13 tasks)
- User Story 3 (P3): Safe destruction (13 tasks)
- Polish phase: Documentation and hardening (13 tasks)

---

## Format Validation

✅ **ALL tasks follow checklist format**:
- Checkbox: `- [ ]`
- Task ID: T001-T121 (sequential)
- Parallelizable marker: [P] where applicable
- Story label: [US1], [US2], [US3] for user story tasks
- Description: Clear action with exact file path

✅ **Task organization verified**:
- Phase 1: Setup (no story labels) ✓
- Phase 2: Foundational (no story labels) ✓
- Phase 3: User Story 1 with [US1] labels ✓
- Phase 4: User Story 2 with [US2] labels ✓
- Phase 5: User Story 3 with [US3] labels ✓
- Phase N: Polish (no story labels) ✓

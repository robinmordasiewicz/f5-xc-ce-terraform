# Naming Convention Refactoring Workflow

This document describes the "nuke and pave" approach for applying the Azure CAF naming convention refactoring.

## Related Issue

GitHub Issue: #98 - Refactor naming conventions to follow Azure CAF and separate hub/workload naming

## Overview

Instead of complex `terraform state mv` operations, we use a simpler destroy/recreate approach for the development environment:

1. **Destroy** existing infrastructure with old naming
2. **Apply** with new Azure CAF compliant naming
3. **Validate** naming conventions and functionality

## Pre-Refactoring State

### Current Naming (Before)
```
Hub Infrastructure:
- xc-ce-hub-vnet
- nva-subnet
- management-subnet

F5 XC Resources:
- xc-ce-ce-01 (VM 1)
- xc-ce-ce-02 (VM 2)
- xc-ce-ce-lb (Load Balancer)
- xc-ce-ce-site (F5 XC Site)
- xc-ce-ce-site-token (Registration Token)
```

### Target Naming (After)
```
Hub Infrastructure (Generic):
- hub-vnet
- snet-hub-external
- snet-hub-management

F5 XC Resources (Specific):
- f5-xc-ce-vm-01 (VM 1)
- f5-xc-ce-vm-02 (VM 2)
- lbi-f5-xc-ce (Load Balancer)
- robinmordasiewicz-f5xc-azure-eastus (F5 XC Site)
- robinmordasiewicz-f5xc-site-token (Registration Token)

F5 XC Site Labels (NEW):
  owner: "r.mordasiewicz"
  github_user: "robinmordasiewicz"
  github_repo: "f5-xc-ce-terraform"
  repo_url: "github.com/robinmordasiewicz/f5-xc-ce-terraform"
  environment: "dev"
  azure_region: "eastus"
  deployment_method: "terraform"
  managed_by: "terraform"
```

## Workflow Steps

### Step 1: Run Baseline Tests
```bash
# Validate current naming before changes
./tests/validate-naming-conventions.sh --mode=current
```

**Expected Result**: ✅ All tests pass (validates current state)

### Step 2: Destroy Existing Infrastructure
```bash
cd terraform/environments/dev
terraform destroy

# Verify all resources destroyed
terraform state list
# Should return empty or only backend resources
```

**Warning**: This will destroy:
- 2 x Azure VMs (F5 XC CE instances)
- 1 x Internal Load Balancer
- 1 x Hub VNet with subnets
- 1 x Spoke VNet with peering
- All associated NSGs, route tables, NICs, public IPs
- F5 XC site registration

### Step 3: Apply with New Naming
```bash
# Apply Terraform with updated naming conventions
terraform apply

# Review plan carefully - all resources should show as "create"
# Confirm the new naming appears in the plan
```

### Step 4: Validate New Naming
```bash
cd ../../.. # Back to project root

# Run target naming validation tests
./tests/validate-naming-conventions.sh --mode=target
```

**Expected Result**: ✅ All tests pass (validates new Azure CAF naming)

### Step 5: Verify F5 XC Site Registration
```bash
# Run deployment verification script
./scripts/verify-f5xc-deployment.sh
```

**Expected Results**:
- ✅ F5 XC site exists with new name: `robinmordasiewicz-f5xc-azure-eastus`
- ✅ Registration token exists: `robinmordasiewicz-f5xc-site-token`
- ✅ VMs registered to F5 XC Console: `f5-xc-ce-vm-01`, `f5-xc-ce-vm-02`
- ✅ Hub VNet: `hub-vnet` (generic, reusable)
- ✅ Load Balancer: `lbi-f5-xc-ce` (Azure CAF compliant)

### Step 6: Verify Terraform Plan Shows No Changes
```bash
cd terraform/environments/dev
terraform plan

# Should show: "No changes. Your infrastructure matches the configuration."
```

## Validation Checklist

- [ ] Baseline tests pass (current naming)
- [ ] Infrastructure successfully destroyed
- [ ] Infrastructure successfully created with new naming
- [ ] Target naming tests pass
- [ ] F5 XC site has new name with owner identifier
- [ ] F5 XC site has all identity labels
- [ ] Hub VNet uses generic naming (no F5 XC branding)
- [ ] F5 XC CE VMs use clear "f5-xc-ce-vm-" prefix
- [ ] Load balancer follows Azure CAF "lbi-" prefix
- [ ] Subnets follow Azure CAF "snet-hub-" prefix
- [ ] VMs successfully registered to F5 XC Console
- [ ] Load balancer health probes passing
- [ ] `terraform plan` shows no changes

## Rollback Procedure

If issues arise, rollback by:

1. Checkout previous commit:
   ```bash
   git checkout HEAD~1
   ```

2. Destroy new infrastructure:
   ```bash
   cd terraform/environments/dev
   terraform destroy
   ```

3. Apply old naming:
   ```bash
   terraform apply
   ```

## Expected Downtime

**Total**: ~20-30 minutes
- Destroy: ~5-10 minutes
- Apply: ~10-15 minutes
- Validation: ~5 minutes

**Impact**: Complete outage during destroy/recreate (acceptable for dev environment)

## Benefits of Nuke-and-Pave Approach

✅ **Simpler**: No complex state migrations
✅ **Cleaner**: Fresh infrastructure with correct naming
✅ **Safer**: No risk of state corruption
✅ **Testable**: Can verify everything works from scratch
✅ **Documented**: Clear before/after state

## Post-Deployment Verification

### Check Azure Resources
```bash
az network vnet list --query "[].name" -o table
az vm list --query "[].name" -o table
az network lb list --query "[].name" -o table
```

### Check F5 XC Console
1. Login to F5 XC Console
2. Navigate to Sites
3. Verify site exists with new name
4. Check site labels contain all identity information
5. Verify VMs are registered and healthy

## Notes

- This workflow is for development environment only
- Production environments would require blue/green deployment or state migration
- F5 XC site recreation causes VMs to re-register (automatic, no manual intervention)
- Azure resources are recreated, so IP addresses and resource IDs will change

## Completion Criteria

This refactoring is complete when:
1. All validation tests pass
2. F5 XC site operational with new naming
3. VMs registered and healthy
4. Load balancer health checks passing
5. Documentation updated
6. PR approved and merged

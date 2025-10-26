# Terraform-Native Diagram Generation

Automatic infrastructure diagram generation integrated directly into the Terraform lifecycle using `null_resource` with intelligent triggers.

## 🎯 Overview

This approach makes diagram generation a **native part of Terraform apply**, automatically triggering diagram updates when infrastructure changes are detected. The diagram generator runs as a provisioner after all resources are created/updated.

### Key Benefits

✅ **Automatic**: Runs as part of `terraform apply` - no manual step needed
✅ **Smart Triggers**: Only regenerates when infrastructure actually changes
✅ **State-Tracked**: Managed by Terraform state, can be destroyed/recreated
✅ **Plan-Visible**: Shows in `terraform plan` when diagrams will regenerate
✅ **Non-Blocking**: Failures don't break your infrastructure deployment
✅ **Optional**: Easily enabled/disabled via variable

## 🚀 Quick Start

### 1. Initial Setup

First, set up the diagram generator tool:

```bash
./scripts/setup-diagram-generator.sh
```

### 2. Configure Terraform Variables

Create `terraform.auto.tfvars` (this file is gitignored):

```hcl
# Enable diagram generation
enable_diagram_generation = true

# Diagram configuration (no credentials needed!)
diagram_config = {
  diagram_title = "Production Infrastructure"
  auto_layout   = true
  enable_drift  = true
  output_dir    = "diagrams"
}
```

**Note**: No credentials required! Draw.io diagrams are generated locally as .drawio files.

### 3. Deploy Infrastructure

```bash
cd terraform/environments/dev
terraform init
terraform plan    # Shows diagram will be generated
terraform apply   # Deploys infrastructure AND generates diagram
```

### 4. View Diagram

The diagram files will be displayed in the Terraform output:

```
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Infrastructure Diagram Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 Draw.io file: F5_XC_CE_Infrastructure.drawio
🖼️  PNG image: F5_XC_CE_Infrastructure.png
💡 Display PNG in README, link to .drawio for editing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Two files are generated**:
- **PNG Image** (`F5_XC_CE_Infrastructure.png`) - Displayed in README.md for easy viewing
- **Draw.io Source** (`F5_XC_CE_Infrastructure.drawio`) - Editable diagram file

**Viewing Options**:
- **In README**: PNG displays automatically in GitHub
- **Edit Diagram**: Click the `.drawio` link in README to edit
- **Draw.io Desktop**: Open the `.drawio` file with [Draw.io Desktop](https://github.com/jgraph/drawio-desktop/releases)
- **diagrams.net**: Import the `.drawio` file at [diagrams.net](https://app.diagrams.net)

## 📝 Configuration

### Via Terraform Variables File

**Recommended for development:**

Create `terraform.auto.tfvars`:

```hcl
enable_diagram_generation = true

diagram_config = {
  diagram_title = "My Infrastructure"
  auto_layout   = true
  enable_drift  = true
  output_dir    = "."  # Repository root
}
```

### Via Environment Variables

**Recommended for CI/CD:**

```bash
# Enable diagram generation
export TF_VAR_enable_diagram_generation=true

# Configure diagram settings (JSON format)
export TF_VAR_diagram_config='{
  "diagram_title": "CI/CD Infrastructure",
  "auto_layout": true,
  "enable_drift": true,
  "output_dir": "."
}'

terraform apply
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `diagram_title` | string | "F5 XC CE Infrastructure" | Title for generated diagram |
| `auto_layout` | bool | true | Enable automatic diagram layout |
| `enable_drift` | bool | true | Detect Terraform vs Azure drift |
| `output_dir` | string | "." | Output directory (repository root for Git version control) |

## 🔄 How It Works

### Trigger Logic

The `null_resource` monitors these infrastructure elements and triggers diagram regeneration when ANY change:

- **VNETs**: Hub/spoke VNET IDs and address spaces
- **Load Balancer**: Load balancer resource ID
- **CE Instances**: VM IDs and sizes
- **F5 XC Site**: Site registration ID
- **Network Topology**: Peering status
- **Configuration**: Location, VM sizing changes

### Execution Flow

```
terraform plan
  ├─ Shows: null_resource.infrastructure_diagram must be replaced
  └─ Indicates diagram will regenerate

terraform apply
  ├─ Creates/updates infrastructure resources
  ├─ Triggers null_resource.infrastructure_diagram
  │   ├─ Checks if diagram generator is installed
  │   ├─ Activates Python virtual environment
  │   ├─ Executes generate-diagram command
  │   │   ├─ Reads Terraform state
  │   │   ├─ Queries Azure Resource Graph
  │   │   ├─ Queries F5 XC Console API
  │   │   ├─ Correlates resources
  │   │   └─ Generates Draw.io diagram (local .drawio file)
  │   └─ Displays local file path in repository root
  └─ Completes successfully (even if diagram fails)
```

### State Management

The diagram generation is tracked in Terraform state:

```hcl
# State includes:
null_resource.infrastructure_diagram[0]
  triggers = {
    hub_vnet_id = "id-abc123..."
    spoke_vnet_id = "id-xyz789..."
    # ... other triggers
  }
```

When any trigger value changes, Terraform will replace the resource and regenerate the diagram.

## 🎨 Terraform Plan Output

### When Diagrams Will Regenerate

```hcl
$ terraform plan

Terraform will perform the following actions:

  # null_resource.infrastructure_diagram[0] must be replaced
-/+ resource "null_resource" "infrastructure_diagram" {
      ~ id       = "8424242424242424242" -> (known after apply)
      ~ triggers = { # forces replacement
          ~ hub_vnet_id = "/subscriptions/.../old-id" -> "/subscriptions/.../new-id"
            # (5 unchanged elements hidden)
        }
    }

Plan: 1 to add, 0 to change, 1 to destroy.
```

### When Diagrams Won't Regenerate

```hcl
$ terraform plan

No changes. Your infrastructure matches the configuration.
```

## 🔧 Advanced Usage

### Disable Diagram Generation

**Temporarily:**

```bash
terraform apply -var="enable_diagram_generation=false"
```

**Permanently:**

Update `terraform.tfvars`:

```hcl
enable_diagram_generation = false
```

### Force Diagram Regeneration

```bash
# Taint the resource to force recreation
terraform taint 'null_resource.infrastructure_diagram[0]'

# Apply to regenerate
terraform apply
```

### Custom Diagram Titles with Timestamps

Modify `diagram.tf`:

```hcl
diagram_title = "Infrastructure - ${formatdate("YYYY-MM-DD", timestamp())}"
```

### Regenerate on Every Apply

Add timestamp to triggers in `diagram.tf`:

```hcl
triggers = {
  # ... existing triggers
  timestamp = timestamp()  # Uncomment this line
}
```

**Warning**: This regenerates diagrams even when infrastructure doesn't change.

## 📊 Outputs

### Check Diagram Status

```bash
terraform output diagram_generation_enabled
# Output: true

terraform output diagram_generation_triggers
# Output:
# {
#   "last_generated" = "2025-10-26T12:34:56Z"
#   "hub_vnet" = "hub-vnet-dev"
#   "spoke_vnet" = "spoke-vnet-dev"
#   "ce_instances" = ["ce-vm-1", "ce-vm-2"]
#   "f5xc_site" = "azure-eastus-site"
# }
```

## 🔍 Troubleshooting

### Diagram Generator Not Found

```
⚠️  Diagram generator not installed. Run: ./scripts/setup-diagram-generator.sh
⚠️  Skipping diagram generation...
```

**Solution:**

```bash
./scripts/setup-diagram-generator.sh
```

### Diagram Generator Issues

If you encounter problems, check:

```bash
# Verify installation
ls -la tools/diagram-generator/.venv/

# Check Python dependencies
source tools/diagram-generator/.venv/bin/activate
pip list
deactivate
```

**Solution:** Re-run setup script if needed:

```bash
./scripts/setup-diagram-generator.sh
```

### Diagram Generation Fails But Apply Succeeds

This is expected behavior - diagram generation is **non-blocking**. Check logs:

```bash
cat diagram-generation.log
```

Common issues:
- Python dependencies not installed correctly
- Azure Resource Graph query failures
- F5 XC API authentication issues
- File permission errors in output directory

### View Detailed Logs

The provisioner creates `diagram-generation.log`:

```bash
cat terraform/environments/dev/diagram-generation.log
```

## 🆚 Comparison: Terraform-Native vs Post-Apply Script

### Terraform-Native (This Approach)

**Advantages:**
- ✅ Integrated into Terraform lifecycle
- ✅ Shows in `terraform plan`
- ✅ Tracked in Terraform state
- ✅ Automatic on every apply
- ✅ Smart triggers (only when needed)

**Disadvantages:**
- ⚠️ Requires Terraform variable configuration
- ⚠️ Runs even for plan-only changes
- ⚠️ Limited to Terraform-initiated deployments

**Best for:**
- Teams using Infrastructure-as-Code workflows
- Automated CI/CD pipelines
- When you want diagrams always in sync

### Post-Apply Script (`./scripts/generate-diagram.sh`)

**Advantages:**
- ✅ Simpler configuration
- ✅ Works outside Terraform
- ✅ Can run on-demand
- ✅ No Terraform state impact

**Disadvantages:**
- ⚠️ Manual execution required
- ⚠️ Not integrated with Terraform lifecycle
- ⚠️ Easy to forget

**Best for:**
- One-off diagram generation
- Troubleshooting and investigation
- Teams not using Terraform exclusively

### Recommended Approach

**Use both:**
- **Terraform-native** for automatic updates in development/CI/CD
- **Post-apply script** for manual diagram generation when needed

```bash
# Automatic (part of terraform apply)
terraform apply  # Diagram generated automatically

# Manual (when you need a fresh diagram without applying)
./scripts/generate-diagram.sh
```

## 🔐 Security Best Practices

### No Credentials Required!

Draw.io diagram generation is completely local - no OAuth, no API keys, no credentials needed!

### Use .auto.tfvars for Local Development

`.auto.tfvars` is gitignored and automatically loaded:

```bash
# Create terraform.auto.tfvars (gitignored)
cat > terraform.auto.tfvars <<EOF
enable_diagram_generation = true
diagram_config = {
  diagram_title = "Dev Infrastructure"
  auto_layout   = true
  enable_drift  = true
  output_dir    = "diagrams"
}
EOF
```

### CI/CD Configuration

For GitHub Actions - no secrets needed:

```yaml
# .github/workflows/terraform-apply.yml
- name: Apply Infrastructure
  env:
    TF_VAR_enable_diagram_generation: "true"
    TF_VAR_diagram_config: |
      {
        "diagram_title": "Production - ${{ github.sha }}",
        "auto_layout": true,
        "enable_drift": true,
        "output_dir": "."
      }
  run: terraform apply -auto-approve
```

## 📚 Related Documentation

- **Initial Setup**: See `docs/DIAGRAM_GENERATOR_INTEGRATION.md`
- **Tool Documentation**: See `tools/diagram-generator/README.md`
- **Post-Apply Script**: See `scripts/generate-diagram.sh`
- **CI/CD Integration**: See `.github/workflows/terraform-apply.yml`

## 🎓 Examples

### Example 1: Development with Auto-Diagrams

```bash
# Setup once
./scripts/setup-diagram-generator.sh

# Configure diagram generation
cat > terraform.auto.tfvars <<EOF
enable_diagram_generation = true
diagram_config = {
  diagram_title = "Dev Environment"
  auto_layout   = true
  enable_drift  = true
  output_dir    = "diagrams"
}
EOF

# Normal workflow - diagrams generated automatically
terraform plan
terraform apply
# Diagram URL displayed after apply
```

### Example 2: Production with Selective Diagrams

```hcl
# terraform.tfvars
enable_diagram_generation = false  # Disabled by default

# Enable only for major changes
```

```bash
# Apply without diagram
terraform apply

# When you need a diagram
terraform apply -var="enable_diagram_generation=true"
```

### Example 3: CI/CD Pipeline

```yaml
# .github/workflows/terraform-apply.yml
- name: Apply Infrastructure
  env:
    TF_VAR_enable_diagram_generation: "true"
    TF_VAR_diagram_config: |
      {
        "diagram_title": "Production - ${{ github.sha }}",
        "auto_layout": true,
        "enable_drift": true,
        "output_dir": "."
      }
  run: terraform apply -auto-approve
```

## 💡 Tips

1. **Start with it disabled** until you confirm the tool works manually
2. **Test with `terraform.auto.tfvars`** for easy local development
3. **No secrets needed** - Draw.io diagrams are generated locally
4. **Review `terraform plan`** to see when diagrams will regenerate
5. **Check logs** in `diagram-generation.log` if issues occur
6. **Taint the resource** to force regeneration without changing infrastructure
7. **View diagrams** in GitHub, Draw.io desktop app, or by importing at diagrams.net
8. **Commit diagrams to Git** for version control and team collaboration

# Automated Infrastructure Diagram Generation
#
# This resource automatically generates infrastructure diagrams when changes are detected.
# It runs as part of the Terraform apply process and only executes when infrastructure
# resources are created, modified, or destroyed.

# Data source for current Azure subscription
data "azurerm_subscription" "current" {}

# Variable to enable/disable diagram generation
variable "enable_diagram_generation" {
  description = "Enable automatic diagram generation after Terraform apply"
  type        = bool
  default     = false # Set to true to enable
}

# Diagram generator configuration
variable "diagram_config" {
  description = "Configuration for diagram generation"
  type = object({
    diagram_title = string
    auto_layout   = bool
    enable_drift  = bool
    output_dir    = string
  })
  default = {
    diagram_title = "F5_XC_CE_Infrastructure"
    auto_layout   = true
    enable_drift  = true
    output_dir    = "../../../" # Repository root (relative to terraform/environments/dev)
  }
}

# Null resource that triggers diagram generation when infrastructure changes
resource "null_resource" "infrastructure_diagram" {
  # Only create if diagram generation is enabled
  count = var.enable_diagram_generation ? 1 : 0

  # Triggers - regenerate diagram when any of these change
  triggers = {
    # Infrastructure changes
    hub_vnet_id      = module.hub_vnet.vnet_id
    spoke_vnet_id    = module.spoke_vnet.vnet_id
    load_balancer_id = module.load_balancer.lb_id
    ce_vm_1_id       = module.ce_appstack_1.vm_id
    ce_vm_2_id       = module.ce_appstack_2.vm_id
    f5xc_site_id     = module.f5_xc_registration.site_id

    # Network topology changes
    hub_address_space   = jsonencode(var.hub_vnet_address_space)
    spoke_address_space = jsonencode(var.spoke_vnet_address_space)
    peering_status      = jsonencode(module.spoke_vnet.peering_status)

    # Configuration changes
    ce_vm_size   = var.ce_vm_size
    azure_region = var.azure_region

    # Force regeneration on timestamp (optional - comment out for only real changes)
    # timestamp           = timestamp()
  }

  # Generate diagram after all resources are created/updated
  provisioner "local-exec" {
    command = <<-EOT
      echo "🎨 Generating infrastructure diagram..."

      # Get project root directory (relative to terraform execution)
      TERRAFORM_DIR="${path.module}"
      PROJECT_ROOT="$TERRAFORM_DIR/../../.."
      DIAGRAM_TOOL="$PROJECT_ROOT/tools/diagram-generator"

      # Check if diagram generator is installed
      if [ ! -d "$DIAGRAM_TOOL/.venv" ]; then
        echo "⚠️  Diagram generator not installed"
        echo "⚠️  Run: cd $DIAGRAM_TOOL && python -m venv .venv && source .venv/bin/activate && pip install -e ."
        echo "⚠️  Skipping diagram generation..."
        exit 0
      fi

      # Verify required environment variables (set by setup-backend.sh)
      if [ -z "$AZURE_SUBSCRIPTION_ID" ]; then
        echo "❌ AZURE_SUBSCRIPTION_ID not set - run scripts/setup-backend.sh first"
        exit 1
      fi

      if [ -z "$TF_VAR_f5_xc_tenant" ] && [ -z "$F5XC_TENANT" ]; then
        echo "❌ F5 XC tenant not configured - run scripts/setup-backend.sh first"
        exit 1
      fi

      # Activate virtual environment
      echo "📦 Activating Python environment..."
      source "$DIAGRAM_TOOL/.venv/bin/activate"

      # Generate diagram using environment-based authentication
      # Authentication credentials are inherited from shell environment (setup-backend.sh)
      echo "🔄 Generating Draw.io diagram from Terraform state..."
      echo "   Azure Subscription: $AZURE_SUBSCRIPTION_ID"
      echo "   F5 XC Tenant: $${TF_VAR_f5_xc_tenant:-$$F5XC_TENANT}"
      echo "   Terraform Path: $TERRAFORM_DIR"
      echo "   Output Dir: ${var.diagram_config.output_dir}"
      echo ""

      # Capture output to parse file paths while displaying to stdout
      OUTPUT=$(python -m diagram_generator.cli \
        --terraform-path "$TERRAFORM_DIR" \
        --diagram-title "${var.diagram_config.diagram_title}" \
        --output-dir "${var.diagram_config.output_dir}" \
        --verbose 2>&1)

      # Display the output
      echo "$OUTPUT"

      # Check exit status and parse output
      if [ $? -eq 0 ]; then
        echo "✅ Diagram generated successfully!"
        DRAWIO_FILE=$(echo "$OUTPUT" | grep -o 'Draw.io file: [^[:space:]]*' | sed 's/Draw.io file: //' | head -1)
        PNG_FILE=$(echo "$OUTPUT" | grep -o 'PNG image: [^[:space:]]*' | sed 's/PNG image: //' | head -1)
        if [ -n "$DRAWIO_FILE" ] && [ -n "$PNG_FILE" ]; then
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "📊 Infrastructure Diagram Generated"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "📄 Draw.io file: $DRAWIO_FILE"
          echo "🖼️  PNG image: $PNG_FILE"
          echo "💡 Display PNG in README, link to .drawio for editing"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo ""
        fi
      else
        echo "⚠️  Diagram generation encountered an error (non-blocking)"
      fi

      # Deactivate virtual environment
      deactivate
    EOT

    interpreter = ["/bin/bash", "-c"]

    # Working directory for execution
    working_dir = path.module

    # Inherit environment variables from shell (includes F5 XC credentials from setup-backend.sh)
    environment = {
      AZURE_SUBSCRIPTION_ID = data.azurerm_subscription.current.subscription_id
      TF_VAR_f5_xc_tenant   = var.f5_xc_tenant
      F5XC_TENANT           = var.f5_xc_tenant
      # VES_P12_PASSWORD, VES_P12_CONTENT inherited from shell environment
    }
  }

  # Ensure this runs after all infrastructure is created
  depends_on = [
    module.hub_vnet,
    module.spoke_vnet,
    module.load_balancer,
    module.ce_appstack_1,
    module.ce_appstack_2,
    module.f5_xc_registration
  ]
}

# Output the diagram generation status
output "diagram_generation_enabled" {
  description = "Whether automatic diagram generation is enabled"
  value       = var.enable_diagram_generation
}

output "diagram_generation_triggers" {
  description = "Trigger values that cause diagram regeneration"
  value = var.enable_diagram_generation ? {
    last_generated = try(null_resource.infrastructure_diagram[0].id, "never")
    hub_vnet       = module.hub_vnet.vnet_name
    spoke_vnet     = module.spoke_vnet.vnet_name
    ce_instances   = [module.ce_appstack_1.vm_name, module.ce_appstack_2.vm_name]
    f5xc_site      = module.f5_xc_registration.site_name
  } : null
}

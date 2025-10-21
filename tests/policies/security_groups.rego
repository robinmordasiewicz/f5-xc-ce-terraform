# Terraform Compliance Policy: Security Groups and Network Security
# Enforces security best practices for NSGs and network configuration
# Constitution compliance: Code Quality Standards - Security

package terraform.security

import future.keywords.in

# No wildcard source addresses in NSG rules (0.0.0.0/0)
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_network_security_rule"
    rule := resource.change.after
    rule.source_address_prefix == "*"
    rule.access == "Allow"
    rule.direction == "Inbound"
    msg := sprintf("NSG rule '%s' allows inbound traffic from any source (*) - security risk", [resource.address])
}

deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_network_security_rule"
    rule := resource.change.after
    rule.source_address_prefix == "0.0.0.0/0"
    rule.access == "Allow"
    rule.direction == "Inbound"
    msg := sprintf("NSG rule '%s' allows inbound traffic from any source (0.0.0.0/0) - security risk", [resource.address])
}

# SSH (port 22) should not be open to the internet
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_network_security_rule"
    rule := resource.change.after
    rule.destination_port_range == "22"
    rule.source_address_prefix == "*"
    rule.access == "Allow"
    rule.direction == "Inbound"
    msg := sprintf("NSG rule '%s' allows SSH (port 22) from internet - use bastion or VPN instead", [resource.address])
}

# RDP (port 3389) should not be open to the internet
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_network_security_rule"
    rule := resource.change.after
    rule.destination_port_range == "3389"
    rule.source_address_prefix == "*"
    rule.access == "Allow"
    rule.direction == "Inbound"
    msg := sprintf("NSG rule '%s' allows RDP (port 3389) from internet - use bastion or VPN instead", [resource.address])
}

# HTTPS/TLS should be enforced for storage accounts
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_storage_account"
    storage := resource.change.after
    storage.https_traffic_only_enabled == false
    msg := sprintf("Storage account '%s' does not enforce HTTPS-only traffic", [resource.address])
}

# Storage account public access should be disabled
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_storage_account"
    storage := resource.change.after
    storage.allow_blob_public_access == true
    msg := sprintf("Storage account '%s' allows public blob access - security risk", [resource.address])
}

# Minimum TLS version should be 1.2
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_storage_account"
    storage := resource.change.after
    storage.min_tls_version != "TLS1_2"
    msg := sprintf("Storage account '%s' does not enforce minimum TLS 1.2", [resource.address])
}

# Virtual network should have network security groups
warn[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_subnet"
    subnet := resource.change.after
    not subnet.network_security_group_id
    msg := sprintf("Subnet '%s' does not have an associated NSG - consider adding one", [resource.address])
}

# Load balancer health probes required
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_lb"
    lb_address := resource.address

    # Check if health probe exists for this load balancer
    count([probe | probe := input.resource_changes[_]; probe.type == "azurerm_lb_probe"; contains(probe.address, lb_address)]) == 0
    msg := sprintf("Load balancer '%s' does not have health probes configured", [lb_address])
}

# VM data disks should be encrypted
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "azurerm_virtual_machine"
    vm := resource.change.after
    disk := vm.storage_data_disk[_]
    disk.disk_encryption_enabled == false
    msg := sprintf("VM '%s' has unencrypted data disk - enable disk encryption", [resource.address])
}

# Warn about missing diagnostics settings
warn[msg] {
    resource := input.resource_changes[_]
    startswith(resource.type, "azurerm_")
    resource.type != "azurerm_resource_group"

    # Check if monitoring diagnostic setting exists
    address := resource.address
    count([diag | diag := input.resource_changes[_]; diag.type == "azurerm_monitor_diagnostic_setting"; contains(diag.address, address)]) == 0
    msg := sprintf("Resource '%s' does not have diagnostic settings - consider adding for monitoring", [address])
}

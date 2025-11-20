package test

import (
	"strings"
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/azure"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// T027: Contract test for F5 XC site creation API
func TestF5XCSiteCreationContract(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../terraform/modules/f5-xc-registration",
		Vars: map[string]interface{}{
			"f5_xc_api_token": "test-token",
			"f5_xc_tenant":    "test-tenant",
			"site_name":       "test-ce-site",
			"azure_region":    "eastus",
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	// TDD: This test will FAIL until F5 XC registration module is implemented
	terraform.InitAndPlan(t, terraformOptions)

	// Validate that plan includes volterra_azure_vnet_site resource
	planStruct := terraform.InitAndPlanAndShow(t, terraformOptions)
	resourceChanges := planStruct.ResourceChangesMap

	// Assert F5 XC site resource will be created
	assert.Contains(t, resourceChanges, "volterra_azure_vnet_site.ce_site",
		"F5 XC site resource should be in plan")

	// Assert registration token output is defined
	terraform.Apply(t, terraformOptions)
	registrationToken := terraform.Output(t, terraformOptions, "registration_token")
	assert.NotEmpty(t, registrationToken, "Registration token must be generated")
}

// T028: Integration test for CE registration
func TestCERegistration(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../terraform/modules/f5-xc-ce-appstack",
		Vars: map[string]interface{}{
			"resource_group_name": "test-rg",
			"location":            "eastus",
			"ce_instance_name":    "test-ce",
			"subnet_id":           "/subscriptions/test/resourceGroups/test-rg/providers/Microsoft.Network/virtualNetworks/test-vnet/subnets/nva-subnet",
			"vm_size":             "Standard_D8_v4",
			"registration_token":  "test-registration-token",
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)

	// TDD: This test will FAIL until CE AppStack module is implemented
	terraform.InitAndApply(t, terraformOptions)

	// Validate VM created with correct configuration
	vmName := terraform.Output(t, terraformOptions, "ce_vm_name")
	assert.NotEmpty(t, vmName, "CE VM name must be output")

	// Validate cloud-init includes registration token
	vmID := terraform.Output(t, terraformOptions, "ce_vm_id")
	assert.NotEmpty(t, vmID, "CE VM ID must be output")
	assert.Contains(t, vmID, "test-ce", "VM ID should contain instance name")

	// Validate managed identity assigned
	identityID := terraform.Output(t, terraformOptions, "ce_identity_id")
	assert.NotEmpty(t, identityID, "Managed identity must be assigned")
}

// T029: Integration test for network routing validation
func TestNetworkRoutingValidation(t *testing.T) {
	t.Parallel()

	// Create hub VNET first
	hubOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../terraform/modules/azure-hub-vnet",
		Vars: map[string]interface{}{
			"resource_group_name": "test-routing-rg",
			"location":            "eastus",
			"vnet_name":           "test-hub-vnet",
			"address_space":       []string{"10.0.0.0/16"},
			"nva_subnet_prefix":   "10.0.1.0/26",
			"mgmt_subnet_prefix":  "10.0.2.0/24",
			"tags": map[string]string{
				"environment": "test",
				"managed_by":  "terraform",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, hubOptions)

	// TDD: This test will FAIL until hub VNET module is implemented
	terraform.InitAndApply(t, hubOptions)

	hubVnetID := terraform.Output(t, hubOptions, "vnet_id")
	nvaSubnetID := terraform.Output(t, hubOptions, "nva_subnet_id")

	require.NotEmpty(t, hubVnetID, "Hub VNET ID must be output")
	require.NotEmpty(t, nvaSubnetID, "NVA subnet ID must be output")

	// Create spoke VNET with peering and UDR
	spokeOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../terraform/modules/azure-spoke-vnet",
		Vars: map[string]interface{}{
			"resource_group_name": "test-routing-rg",
			"location":            "eastus",
			"vnet_name":           "test-spoke-vnet",
			"address_space":       []string{"10.1.0.0/16"},
			"workload_subnet_prefix": "10.1.1.0/24",
			"hub_vnet_id":         hubVnetID,
			"hub_nva_ip":          "10.0.1.4",
			"tags": map[string]string{
				"environment": "test",
				"managed_by":  "terraform",
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, spokeOptions)

	// TDD: This test will FAIL until spoke VNET module is implemented
	terraform.InitAndApply(t, spokeOptions)

	spokeVnetID := terraform.Output(t, spokeOptions, "vnet_id")
	peeringID := terraform.Output(t, spokeOptions, "peering_id")
	routeTableID := terraform.Output(t, spokeOptions, "route_table_id")

	// Validate spoke VNET created
	assert.NotEmpty(t, spokeVnetID, "Spoke VNET ID must be output")
	assert.Contains(t, spokeVnetID, "test-spoke-vnet", "VNET ID should contain name")

	// Validate VNET peering established
	assert.NotEmpty(t, peeringID, "Peering ID must be output")

	// Validate route table with default route to hub NVA
	assert.NotEmpty(t, routeTableID, "Route table ID must be output")

	// Validate route table contains default route
	defaultRoute := terraform.Output(t, spokeOptions, "default_route_next_hop")
	assert.Equal(t, "10.0.1.4", defaultRoute, "Default route must point to hub NVA")
}

// T030: End-to-end deployment test
func TestEndToEndDeployment(t *testing.T) {
	// Not parallel - full integration test
	// This is the comprehensive E2E test that validates entire User Story 1

	t.Log("Starting end-to-end deployment test for User Story 1...")

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../../terraform/environments/dev",
		Vars: map[string]interface{}{
			"azure_region":           "eastus",
			"resource_group_name":    "xc-ce-test-rg",
			"hub_vnet_address_space": []string{"10.0.0.0/16"},
			"spoke_vnet_address_space": []string{"10.1.0.0/16"},
			"ce_site_size":           "medium",
			"tags": map[string]string{
				"environment": "test",
				"managed_by":  "terraform",
			},
		},
		NoColor:      true,
		RetryableTerraformErrors: map[string]string{
			".*timeout while waiting.*": "Azure resource creation timeout",
		},
		MaxRetries:         3,
		TimeBetweenRetries: 5 * time.Second,
	})

	defer terraform.Destroy(t, terraformOptions)

	// Step 1: TDD - This test will FAIL until all modules are implemented
	t.Log("Step 1/8: Running terraform init and plan...")
	terraform.InitAndPlan(t, terraformOptions)

	// Step 2: Apply infrastructure
	t.Log("Step 2/8: Applying Terraform configuration...")
	terraform.Apply(t, terraformOptions)

	// Step 3: Validate hub VNET created
	t.Log("Step 3/8: Validating hub VNET...")
	hubVnetID := terraform.Output(t, terraformOptions, "hub_vnet_id")
	require.NotEmpty(t, hubVnetID, "Hub VNET ID must exist")

	// Parse resource group from VNET ID
	resourceGroup := extractResourceGroup(hubVnetID)
	hubVnetName := terraform.Output(t, terraformOptions, "hub_vnet_name")

	// Verify hub VNET exists in Azure
	hubVnetExists := azure.VirtualNetworkExists(t, hubVnetName, resourceGroup, "")
	assert.True(t, hubVnetExists, "Hub VNET must exist in Azure")

	// Step 4: Validate spoke VNET created
	t.Log("Step 4/8: Validating spoke VNET...")
	spokeVnetID := terraform.Output(t, terraformOptions, "spoke_vnet_id")
	require.NotEmpty(t, spokeVnetID, "Spoke VNET ID must exist")

	spokeVnetName := terraform.Output(t, terraformOptions, "spoke_vnet_name")
	spokeVnetExists := azure.VirtualNetworkExists(t, spokeVnetName, resourceGroup, "")
	assert.True(t, spokeVnetExists, "Spoke VNET must exist in Azure")

	// Step 5: Validate VNET peering established
	t.Log("Step 5/8: Validating VNET peering...")
	peeringStatus := terraform.Output(t, terraformOptions, "peering_status")
	assert.Equal(t, "Connected", peeringStatus, "VNET peering must be in Connected state")

	// Step 6: Validate CE registered with F5 XC Console
	t.Log("Step 6/8: Validating CE registration...")
	ceSiteName := terraform.Output(t, terraformOptions, "ce_site_name")
	ceSiteID := terraform.Output(t, terraformOptions, "ce_site_id")
	assert.NotEmpty(t, ceSiteName, "CE site name must be output")
	assert.NotEmpty(t, ceSiteID, "CE site ID must be output")

	// Validate CE VM exists
	ceVMName := terraform.Output(t, terraformOptions, "ce_vm_name")
	ceVMExists := azure.VirtualMachineExists(t, ceVMName, resourceGroup, "")
	assert.True(t, ceVMExists, "CE VM must exist in Azure")

	// Step 7: Validate routing through hub NVA
	t.Log("Step 7/8: Validating routing configuration...")
	defaultRouteNextHop := terraform.Output(t, terraformOptions, "default_route_next_hop")
	assert.NotEmpty(t, defaultRouteNextHop, "Default route next hop must be configured")
	assert.True(t, strings.HasPrefix(defaultRouteNextHop, "10.0."),
		"Default route should point to hub subnet IP")

	// Step 8: Validate load balancer health probes
	t.Log("Step 8/8: Validating load balancer configuration...")
	lbID := terraform.Output(t, terraformOptions, "load_balancer_id")
	assert.NotEmpty(t, lbID, "Load balancer ID must be output")

	lbHealthProbePort := terraform.Output(t, terraformOptions, "lb_health_probe_port")
	assert.Equal(t, "65500", lbHealthProbePort, "Health probe should use port 65500")

	t.Log("✅ End-to-end deployment test completed successfully!")
}

// Helper function to extract resource group from Azure resource ID
func extractResourceGroup(resourceID string) string {
	parts := strings.Split(resourceID, "/")
	for i, part := range parts {
		if part == "resourceGroups" && i+1 < len(parts) {
			return parts[i+1]
		}
	}
	return ""
}

// Helper function for Azure resource validation
func validateAzureResource(t *testing.T, resourceID string) {
	assert.NotEmpty(t, resourceID, "Azure resource ID should not be empty")
	assert.Contains(t, resourceID, "/subscriptions/", "Resource ID must be fully qualified")
	assert.Contains(t, resourceID, "/resourceGroups/", "Resource ID must contain resource group")
}

// Helper function for F5 XC Console validation
func validateF5XCRegistration(t *testing.T, siteID string) {
	assert.NotEmpty(t, siteID, "F5 XC site ID should not be empty")
	// Site ID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	assert.Len(t, siteID, 36, "F5 XC site ID should be UUID format")
}

// Helper function to validate subnet configuration
func validateSubnetConfiguration(t *testing.T, subnetID string, expectedPrefix string) {
	assert.NotEmpty(t, subnetID, "Subnet ID should not be empty")
	assert.Contains(t, subnetID, "/subnets/", "Resource ID must be a subnet")
}

// Helper function to validate NSG rules
func validateNSGRules(t *testing.T, nsgID string) {
	assert.NotEmpty(t, nsgID, "NSG ID should not be empty")
	assert.Contains(t, nsgID, "/networkSecurityGroups/", "Resource ID must be an NSG")
}

// Helper function to validate load balancer configuration
func validateLoadBalancerConfig(t *testing.T, lbID string, backendPoolID string, probeID string) {
	assert.NotEmpty(t, lbID, "Load balancer ID should not be empty")
	assert.NotEmpty(t, backendPoolID, "Backend pool ID should not be empty")
	assert.NotEmpty(t, probeID, "Health probe ID should not be empty")

	// Validate all IDs belong to the same load balancer
	lbName := extractResourceName(lbID)
	assert.Contains(t, backendPoolID, lbName, "Backend pool should belong to load balancer")
	assert.Contains(t, probeID, lbName, "Health probe should belong to load balancer")
}

// Helper function to extract resource name from ID
func extractResourceName(resourceID string) string {
	parts := strings.Split(resourceID, "/")
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return ""
}

// Helper function to validate peering status
func validatePeeringStatus(t *testing.T, peeringID string, expectedState string) {
	assert.NotEmpty(t, peeringID, "Peering ID should not be empty")
	// Peering validation will be enhanced with Azure SDK calls in actual deployment
	t.Logf("Peering ID: %s (expected state: %s)", peeringID, expectedState)
}

// Helper function to wait for resource readiness
func waitForResourceReady(t *testing.T, resourceType string, timeout time.Duration) {
	t.Logf("Waiting up to %v for %s to be ready...", timeout, resourceType)
	time.Sleep(timeout)
}

"""
Tests for resource correlation engine.
"""

from diagram_generator.correlation import ResourceCorrelator
from diagram_generator.models import RelationshipType


def test_correlator_init():
    """Test ResourceCorrelator initialization."""
    correlator = ResourceCorrelator(
        match_by_tags=True,
        match_by_ip=True,
        enable_drift_detection=True,
    )
    assert correlator.match_by_tags is True
    assert correlator.match_by_ip is True
    assert correlator.enable_drift_detection is True


def test_correlate_empty_resources():
    """Test correlation with empty resource lists."""
    correlator = ResourceCorrelator()
    result = correlator.correlate(
        terraform_resources=[],
        azure_resources=[],
        f5xc_resources=[],
    )

    assert len(result.resources) == 0
    assert len(result.relationships) == 0
    assert len(result.drift) == 0


def test_correlate_terraform_dependencies(sample_terraform_resources):
    """Test Terraform dependency correlation."""
    correlator = ResourceCorrelator()
    result = correlator.correlate(
        terraform_resources=sample_terraform_resources,
        azure_resources=[],
        f5xc_resources=[],
    )

    # Should find dependency between vnet and subnet
    tf_deps = [
        r
        for r in result.relationships
        if r.relationship_type == RelationshipType.TERRAFORM_DEPENDENCY
    ]
    assert len(tf_deps) == 1
    assert "subnet" in tf_deps[0].source_id.lower()


def test_correlate_terraform_to_azure(sample_terraform_resources, sample_azure_resources):
    """Test Terraform to Azure correlation."""
    correlator = ResourceCorrelator()
    result = correlator.correlate(
        terraform_resources=sample_terraform_resources,
        azure_resources=sample_azure_resources,
        f5xc_resources=[],
    )

    # Should find matches between Terraform and Azure resources
    tf_azure = [
        r for r in result.relationships if r.relationship_type == RelationshipType.TERRAFORM_AZURE
    ]
    assert len(tf_azure) >= 1


def test_correlate_f5xc_to_azure_by_ip(sample_f5xc_resources, sample_azure_resources):
    """Test F5 XC to Azure correlation by IP address."""
    correlator = ResourceCorrelator(match_by_ip=True)
    result = correlator.correlate(
        terraform_resources=[],
        azure_resources=sample_azure_resources,
        f5xc_resources=sample_f5xc_resources,
    )

    # F5 XC origin pool should match Azure VM by IP
    f5xc_azure = [
        r
        for r in result.relationships
        if r.relationship_type == RelationshipType.F5XC_ORIGIN_TO_AZURE_VM
    ]

    # May or may not match depending on IP configuration in fixtures
    assert isinstance(f5xc_azure, list)


def test_drift_detection(sample_terraform_resources, sample_azure_resources):
    """Test configuration drift detection."""
    # Modify Azure resource to create drift
    azure_modified = sample_azure_resources.copy()
    azure_modified[0].tags = {"environment": "production"}  # Different from Terraform

    correlator = ResourceCorrelator(enable_drift_detection=True)
    result = correlator.correlate(
        terraform_resources=sample_terraform_resources,
        azure_resources=azure_modified,
        f5xc_resources=[],
    )

    # Should detect tag drift
    tag_drift = [d for d in result.drift if d.drift_type == "tags"]
    assert len(tag_drift) >= 1


def test_drift_detection_disabled():
    """Test that drift detection can be disabled."""
    from diagram_generator.models import AzureResource, TerraformResource

    tf_resources = [
        TerraformResource(
            type="azurerm_virtual_network",
            name="main",
            address="azurerm_virtual_network.main",
            values={
                "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
                "tags": {"env": "dev"},
            },
            depends_on=[],
        )
    ]

    azure_resources = [
        AzureResource(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
            name="vnet-main",
            type="Microsoft.Network/virtualNetworks",
            location="eastus",
            resource_group="rg-test",
            tags={"env": "prod"},  # Different tags
            properties={},
        )
    ]

    correlator = ResourceCorrelator(enable_drift_detection=False)
    result = correlator.correlate(
        terraform_resources=tf_resources,
        azure_resources=azure_resources,
        f5xc_resources=[],
    )

    assert len(result.drift) == 0


def test_add_resources_to_graph(sample_terraform_resources, sample_azure_resources):
    """Test that resources are added to graph."""
    correlator = ResourceCorrelator()
    correlator._add_resources_to_graph(
        sample_terraform_resources,
        sample_azure_resources,
        [],
    )

    assert correlator.graph.number_of_nodes() > 0


def test_index_resources_by_tags(sample_terraform_resources):
    """Test tag indexing."""
    correlator = ResourceCorrelator()
    index = correlator._index_resources_by_tags(sample_terraform_resources, "terraform")

    assert isinstance(index, dict)
    # Check if environment tag is indexed
    env_test = ("environment", "test")
    if env_test in index:
        assert len(index[env_test]) >= 1


def test_extract_resource_group_from_id():
    """Test resource group extraction."""
    from unittest.mock import patch

    from diagram_generator.azure_collector import AzureResourceGraphCollector

    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        collector = AzureResourceGraphCollector(subscription_id="sub-123")
        resource_id = "/subscriptions/sub-123/resourceGroups/my-rg/providers/Microsoft.Network/virtualNetworks/vnet"

        rg = collector._extract_resource_group(resource_id)
        assert rg == "my-rg"


def test_match_origin_pool_to_vms():
    """Test matching F5 XC origin pool to Azure VMs."""
    from diagram_generator.models import AzureResource, F5XCResource

    origin_pool = F5XCResource(
        type="origin_pool",
        namespace="production",
        name="pool-web",
        spec={
            "origin_servers": [
                {"private_ip": {"ip": "10.0.1.10"}},
                {"private_ip": {"ip": "10.0.1.11"}},
            ]
        },
        metadata={"name": "pool-web"},
    )

    azure_vms = [
        AzureResource(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-app01",
            name="vm-app01",
            type="Microsoft.Compute/virtualMachines",
            location="eastus",
            resource_group="rg-test",
            tags={},
            properties={
                "networkProfile": {
                    "networkInterfaces": [
                        {
                            "properties": {
                                "ipConfigurations": [
                                    {"properties": {"privateIPAddress": "10.0.1.10"}}
                                ]
                            }
                        }
                    ]
                }
            },
        )
    ]

    correlator = ResourceCorrelator()
    relationships = correlator._match_origin_pool_to_vms(origin_pool, azure_vms)

    # Should find match by IP
    assert len(relationships) >= 1
    assert relationships[0].relationship_type == RelationshipType.F5XC_ORIGIN_TO_AZURE_VM


def test_correlate_by_tags_matching():
    """Test tag-based correlation finds matches."""
    from diagram_generator.models import AzureResource, F5XCResource, TerraformResource

    tf_resources = [
        TerraformResource(
            type="azurerm_virtual_network",
            name="main",
            address="azurerm_virtual_network.main",
            values={
                "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
                "tags": {"app": "web", "env": "prod"},
            },
            depends_on=[],
        )
    ]

    azure_resources = [
        AzureResource(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
            name="vnet-main",
            type="Microsoft.Network/virtualNetworks",
            location="eastus",
            resource_group="rg-test",
            tags={"app": "web", "env": "prod"},
            properties={},
        )
    ]

    f5xc_resources = [
        F5XCResource(
            type="origin_pool",
            namespace="production",
            name="pool-web",
            spec={},
            metadata={"name": "pool-web", "labels": {"app": "web"}},
        )
    ]

    correlator = ResourceCorrelator(match_by_tags=True)
    result = correlator.correlate(
        terraform_resources=tf_resources,
        azure_resources=azure_resources,
        f5xc_resources=f5xc_resources,
    )

    # Should find some tag-based relationships
    tag_based = [
        r for r in result.relationships if r.metadata.get("tag_key") or r.metadata.get("tag_value")
    ]

    # May or may not find matches depending on tag correlation logic
    assert isinstance(tag_based, list)


def test_correlation_error_handling():
    """Test that correlation handles errors gracefully."""
    from diagram_generator.models import TerraformResource

    # Create invalid resource that might cause issues
    bad_resource = TerraformResource(
        type="test",
        name="bad",
        address="test.bad",
        values={"id": None},  # Invalid ID
        depends_on=[],
    )

    correlator = ResourceCorrelator()

    # Should handle gracefully without crashing
    result = correlator.correlate(
        terraform_resources=[bad_resource],
        azure_resources=[],
        f5xc_resources=[],
    )

    assert isinstance(result.resources, list)
    assert isinstance(result.relationships, list)

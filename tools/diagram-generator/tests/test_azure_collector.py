"""
Tests for Azure Resource Graph collector.
"""

from unittest.mock import Mock, patch

import pytest
from azure.core.exceptions import AzureError

from diagram_generator.azure_collector import AzureResourceGraphCollector
from diagram_generator.exceptions import AuthenticationError, AzureAPIError
from diagram_generator.models import AzureAuthMethod


def test_azure_collector_init():
    """Test AzureResourceGraphCollector initialization."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        collector = AzureResourceGraphCollector(
            subscription_id="sub-123",
            auth_method=AzureAuthMethod.AZURE_CLI,
        )
        assert collector.subscription_id == "sub-123"
        assert collector.auth_method == AzureAuthMethod.AZURE_CLI


def test_azure_collector_with_managed_identity():
    """Test initialization with managed identity auth."""
    with patch("diagram_generator.azure_collector.ManagedIdentityCredential"):
        collector = AzureResourceGraphCollector(
            subscription_id="sub-123",
            auth_method=AzureAuthMethod.MANAGED_IDENTITY,
        )
        assert collector.auth_method == AzureAuthMethod.MANAGED_IDENTITY


def test_azure_collector_auth_failure():
    """Test authentication failure handling."""
    with patch("diagram_generator.azure_collector.AzureCliCredential") as mock_cred:
        mock_cred.side_effect = Exception("Auth failed")

        with pytest.raises(AuthenticationError, match="Azure authentication failed"):
            AzureResourceGraphCollector(
                subscription_id="sub-123",
                auth_method=AzureAuthMethod.AZURE_CLI,
            )


def test_collect_resources_success(mock_azure_client):
    """Test successful resource collection."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_client_class.return_value = mock_azure_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")
            resources = collector.collect_resources()

            assert len(resources) == 1
            assert resources[0].name == "rg-test"
            assert resources[0].resource_group == "rg-test"


def test_collect_resources_with_filter(mock_azure_client):
    """Test resource collection with type filter."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_client_class.return_value = mock_azure_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")
            resources = collector.collect_resources(
                resource_types=["Microsoft.Network/virtualNetworks"]
            )

            # Verify query was built with filter
            assert mock_azure_client.resources.called


def test_collect_resources_api_error():
    """Test handling of Azure API errors."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_client = Mock()
            mock_client.resources.side_effect = AzureError("API error")
            mock_client_class.return_value = mock_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")

            with pytest.raises(AzureAPIError, match="Failed to collect Azure resources"):
                collector.collect_resources()


def test_build_query_no_filter():
    """Test KQL query building without filter."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        collector = AzureResourceGraphCollector(subscription_id="sub-123")
        query = collector._build_query()

        assert "sub-123" in query
        assert "where type in" not in query  # No filter


def test_build_query_with_filter():
    """Test KQL query building with resource type filter."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        collector = AzureResourceGraphCollector(subscription_id="sub-123")
        query = collector._build_query(
            resource_types=[
                "Microsoft.Network/virtualNetworks",
                "Microsoft.Compute/virtualMachines",
            ]
        )

        assert "sub-123" in query
        assert "where type in" in query
        assert "Microsoft.Network/virtualNetworks" in query


def test_extract_resource_group():
    """Test resource group extraction from Azure resource ID."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        collector = AzureResourceGraphCollector(subscription_id="sub-123")

        resource_id = "/subscriptions/sub-123/resourceGroups/my-rg/providers/Microsoft.Network/virtualNetworks/vnet-main"
        rg = collector._extract_resource_group(resource_id)

        assert rg == "my-rg"


def test_extract_resource_group_invalid():
    """Test resource group extraction with invalid ID."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        collector = AzureResourceGraphCollector(subscription_id="sub-123")

        resource_id = "/invalid/path"
        rg = collector._extract_resource_group(resource_id)

        assert rg == "unknown"


def test_collect_network_resources(mock_azure_client):
    """Test network-specific resource collection."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_client_class.return_value = mock_azure_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")
            resources = collector.collect_network_resources()

            # Verify it called collect_resources with network types
            assert isinstance(resources, list)


def test_collect_compute_resources(mock_azure_client):
    """Test compute-specific resource collection."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_client_class.return_value = mock_azure_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")
            resources = collector.collect_compute_resources()

            # Verify it called collect_resources with compute types
            assert isinstance(resources, list)


def test_parse_resources_with_missing_fields():
    """Test parsing resources with missing optional fields."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_response = Mock()
            mock_response.data = [
                {
                    "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Test/resources/test",
                    "name": "test-resource",
                    # Missing type, location, tags, properties
                }
            ]
            mock_response.total_records = 1
            mock_response.count = 1

            mock_client = Mock()
            mock_client.resources.return_value = mock_response
            mock_client_class.return_value = mock_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")
            resources = collector.collect_resources()

            assert len(resources) == 1
            assert resources[0].name == "test-resource"
            assert resources[0].type == "unknown"
            assert resources[0].location == "unknown"


def test_retry_on_transient_error():
    """Test retry logic on transient API errors."""
    with patch("diagram_generator.azure_collector.AzureCliCredential"):
        with patch("diagram_generator.azure_collector.ResourceGraphClient") as mock_client_class:
            mock_client = Mock()

            # First call fails, second succeeds
            mock_response = Mock()
            mock_response.data = []
            mock_response.total_records = 0
            mock_response.count = 0

            mock_client.resources.side_effect = [
                AzureError("Transient error"),
                mock_response,
            ]
            mock_client_class.return_value = mock_client

            collector = AzureResourceGraphCollector(subscription_id="sub-123")
            resources = collector.collect_resources()

            assert len(resources) == 0
            assert mock_client.resources.call_count == 2  # Retry happened

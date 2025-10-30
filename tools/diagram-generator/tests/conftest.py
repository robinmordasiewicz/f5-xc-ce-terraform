"""
Pytest configuration and fixtures for diagram generator tests.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest
from diagram_generator.models import AzureResource, F5XCResource, TerraformResource


@pytest.fixture
def mock_terraform_state() -> dict[str, Any]:
    """Mock Terraform state JSON."""
    return {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "azurerm_virtual_network",
                        "name": "main",
                        "address": "azurerm_virtual_network.main",
                        "values": {
                            "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
                            "name": "vnet-main",
                            "location": "eastus",
                            "address_space": ["10.0.0.0/16"],
                            "tags": {"environment": "test", "managed_by": "terraform"},
                        },
                        "depends_on": [],
                    },
                    {
                        "type": "azurerm_subnet",
                        "name": "internal",
                        "address": "azurerm_subnet.internal",
                        "values": {
                            "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main/subnets/subnet-internal",
                            "name": "subnet-internal",
                            "address_prefixes": ["10.0.1.0/24"],
                            "tags": {},
                        },
                        "depends_on": ["azurerm_virtual_network.main"],
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_azure_resources() -> list[dict[str, Any]]:
    """Mock Azure Resource Graph query results."""
    return [
        {
            "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
            "name": "vnet-main",
            "type": "Microsoft.Network/virtualNetworks",
            "location": "eastus",
            "resourceGroup": "rg-test",
            "tags": {"environment": "test"},
            "properties": {
                "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]},
                "provisioningState": "Succeeded",
            },
        },
        {
            "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-app01",
            "name": "vm-app01",
            "type": "Microsoft.Compute/virtualMachines",
            "location": "eastus",
            "resourceGroup": "rg-test",
            "tags": {"app": "web"},
            "properties": {
                "hardwareProfile": {"vmSize": "Standard_D2s_v3"},
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
                },
            },
        },
    ]


@pytest.fixture
def mock_f5xc_resources() -> dict[str, list[dict[str, Any]]]:
    """Mock F5 XC API response."""
    return {
        "items": [
            {
                "metadata": {
                    "name": "pool-web",
                    "namespace": "production",
                    "labels": {"app": "web"},
                },
                "spec": {
                    "origin_servers": [
                        {
                            "private_ip": {"ip": "10.0.1.10"},
                        }
                    ],
                    "port": 80,
                    "loadbalancer_algorithm": "ROUND_ROBIN",
                },
            }
        ]
    }


@pytest.fixture
def sample_terraform_resources() -> list[TerraformResource]:
    """Sample TerraformResource objects."""
    return [
        TerraformResource(
            type="azurerm_virtual_network",
            name="main",
            address="azurerm_virtual_network.main",
            values={
                "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
                "name": "vnet-main",
                "location": "eastus",
                "tags": {"environment": "test"},
            },
            depends_on=[],
        ),
        TerraformResource(
            type="azurerm_subnet",
            name="internal",
            address="azurerm_subnet.internal",
            values={
                "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main/subnets/subnet-internal",
                "name": "subnet-internal",
            },
            depends_on=["azurerm_virtual_network.main"],
        ),
    ]


@pytest.fixture
def sample_azure_resources() -> list[AzureResource]:
    """Sample AzureResource objects."""
    return [
        AzureResource(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
            name="vnet-main",
            type="Microsoft.Network/virtualNetworks",
            location="eastus",
            resource_group="rg-test",
            tags={"environment": "test"},
            properties={"addressSpace": {"addressPrefixes": ["10.0.0.0/16"]}},
        ),
        AzureResource(
            id="/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Compute/virtualMachines/vm-app01",
            name="vm-app01",
            type="Microsoft.Compute/virtualMachines",
            location="eastus",
            resource_group="rg-test",
            tags={"app": "web"},
            properties={"hardwareProfile": {"vmSize": "Standard_D2s_v3"}},
        ),
    ]


@pytest.fixture
def sample_f5xc_resources() -> list[F5XCResource]:
    """Sample F5XCResource objects."""
    return [
        F5XCResource(
            type="origin_pool",
            namespace="production",
            name="pool-web",
            spec={
                "origin_servers": [{"private_ip": {"ip": "10.0.1.10"}}],
                "port": 80,
            },
            metadata={"name": "pool-web", "labels": {"app": "web"}},
        )
    ]


@pytest.fixture
def mock_terraform_command(monkeypatch):
    """Mock subprocess.run for terraform commands."""

    def mock_run(*args, **kwargs):
        mock_result = Mock()
        mock_result.stdout = json.dumps(
            {
                "values": {
                    "root_module": {
                        "resources": [
                            {
                                "type": "azurerm_resource_group",
                                "name": "test",
                                "address": "azurerm_resource_group.test",
                                "values": {"name": "rg-test"},
                                "depends_on": [],
                            }
                        ]
                    }
                }
            }
        )
        mock_result.returncode = 0
        return mock_result

    monkeypatch.setattr("subprocess.run", mock_run)


@pytest.fixture
def mock_azure_client(monkeypatch):
    """Mock Azure Resource Graph client."""
    mock_client = MagicMock()
    mock_response = Mock()
    mock_response.data = [
        {
            "id": "/subscriptions/sub-123/resourceGroups/rg-test",
            "name": "rg-test",
            "type": "Microsoft.Resources/resourceGroups",
            "location": "eastus",
            "resourceGroup": "rg-test",
            "tags": {},
            "properties": {},
        }
    ]
    mock_response.total_records = 1
    mock_response.count = 1
    mock_client.resources.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_f5xc_session(monkeypatch):
    """Mock requests session for F5 XC API."""
    mock_session = MagicMock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "items": [
            {
                "metadata": {"name": "test-resource"},
                "spec": {"test": "data"},
            }
        ]
    }
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    return mock_session


@pytest.fixture
def mock_lucid_auth(monkeypatch):
    """Mock Lucidchart authentication."""

    class MockLucidAuthClient:
        def __init__(self, *args, **kwargs):
            self.access_token = "mock-access-token"

        def authenticate(self, force_reauth=False):
            return self.access_token

        def get_auth_header(self):
            return {"Authorization": f"Bearer {self.access_token}"}

    return MockLucidAuthClient


@pytest.fixture
def temp_terraform_dir(tmp_path: Path) -> Path:
    """Create temporary Terraform directory with state."""
    terraform_dir = tmp_path / "terraform"
    terraform_dir.mkdir()

    # Create mock .terraform directory
    (terraform_dir / ".terraform").mkdir()

    return terraform_dir

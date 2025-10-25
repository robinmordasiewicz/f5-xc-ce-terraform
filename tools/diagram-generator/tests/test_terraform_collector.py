"""
Tests for Terraform state collector.
"""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from diagram_generator.exceptions import TerraformStateError
from diagram_generator.terraform_collector import TerraformStateCollector


def test_terraform_collector_init():
    """Test TerraformStateCollector initialization."""
    collector = TerraformStateCollector()
    assert collector.state_path is not None


def test_terraform_collector_with_path(tmp_path):
    """Test TerraformStateCollector with custom path."""
    collector = TerraformStateCollector(state_path=str(tmp_path))
    assert str(collector.state_path) == str(tmp_path)


def test_collect_resources_success(mock_terraform_state):
    """Test successful resource collection."""
    with patch("subprocess.run") as mock_run:
        # Mock successful terraform command
        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_terraform_state)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        collector = TerraformStateCollector()
        resources = collector.collect_resources()

        assert len(resources) == 2
        assert resources[0].type == "azurerm_virtual_network"
        assert resources[0].name == "main"
        assert resources[1].type == "azurerm_subnet"
        assert resources[1].depends_on == ["azurerm_virtual_network.main"]


def test_collect_resources_terraform_not_found():
    """Test error when terraform command not found."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("terraform not found")

        collector = TerraformStateCollector()
        with pytest.raises(TerraformStateError, match="terraform command not found"):
            collector.collect_resources()


def test_collect_resources_command_failure():
    """Test error when terraform command fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="terraform show -json", stderr="Error: No state file"
        )

        collector = TerraformStateCollector()
        with pytest.raises(TerraformStateError, match="terraform show command failed"):
            collector.collect_resources()


def test_collect_resources_invalid_json():
    """Test error when terraform returns invalid JSON."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.stdout = "not valid json"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        collector = TerraformStateCollector()
        with pytest.raises(TerraformStateError, match="Invalid JSON"):
            collector.collect_resources()


def test_parse_resources_empty_state():
    """Test parsing empty Terraform state."""
    collector = TerraformStateCollector()
    state_data = {"values": {"root_module": {"resources": []}}}

    resources = collector._parse_resources(state_data)
    assert len(resources) == 0


def test_parse_resources_missing_fields():
    """Test parsing resources with missing fields."""
    collector = TerraformStateCollector()
    state_data = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        # Missing required fields
                    }
                ]
            }
        }
    }

    resources = collector._parse_resources(state_data)
    # Should handle gracefully and continue
    assert len(resources) == 0 or resources[0].type == "unknown"


def test_parse_resources_with_values(sample_terraform_resources):
    """Test that resource values are properly captured."""
    with patch("subprocess.run") as mock_run:
        mock_state = {
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "type": "azurerm_virtual_network",
                            "name": "main",
                            "address": "azurerm_virtual_network.main",
                            "values": {
                                "id": "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-main",
                                "tags": {"environment": "test"},
                            },
                            "depends_on": [],
                        }
                    ]
                }
            }
        }
        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_state)
        mock_run.return_value = mock_result

        collector = TerraformStateCollector()
        resources = collector.collect_resources()

        assert len(resources) == 1
        assert "id" in resources[0].values
        assert "tags" in resources[0].values
        assert resources[0].values["tags"]["environment"] == "test"


def test_retry_on_failure():
    """Test retry logic on transient failures."""
    with patch("subprocess.run") as mock_run:
        # First call fails, second succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(returncode=1, cmd="terraform", stderr="timeout"),
            Mock(stdout=json.dumps({"values": {"root_module": {"resources": []}}})),
        ]

        collector = TerraformStateCollector()
        resources = collector.collect_resources()

        assert len(resources) == 0
        assert mock_run.call_count == 2  # Retry happened

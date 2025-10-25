"""
Terraform state collection module.

Extracts resources and dependencies from Terraform state files.
"""

import json
import subprocess
from pathlib import Path
from typing import List, Optional

from diagram_generator.exceptions import TerraformStateError
from diagram_generator.models import TerraformResource
from diagram_generator.utils import get_logger, retry_on_exception

logger = get_logger(__name__)


class TerraformStateCollector:
    """Collects and parses Terraform state data."""

    def __init__(self, state_path: Optional[str] = None):
        """
        Initialize Terraform state collector.

        Args:
            state_path: Path to Terraform directory (uses current directory if None)
        """
        self.state_path = Path(state_path) if state_path else Path.cwd()
        logger.info("Terraform collector initialized", path=str(self.state_path))

    @retry_on_exception(max_attempts=2, delay=1.0, exceptions=(subprocess.SubprocessError,))
    def collect_resources(self) -> List[TerraformResource]:
        """
        Collect all Terraform resources from state.

        Returns:
            List of Terraform resources

        Raises:
            TerraformStateError: If state cannot be read or parsed
        """
        logger.info("Collecting Terraform state")

        try:
            state_data = self._get_terraform_state()
            resources = self._parse_resources(state_data)
            logger.info("Terraform resources collected", count=len(resources))
            return resources

        except Exception as e:
            logger.error("Failed to collect Terraform resources", error=str(e))
            raise TerraformStateError(f"Failed to collect Terraform state: {e}") from e

    def _get_terraform_state(self) -> dict:
        """
        Execute terraform show -json to get state.

        Returns:
            Parsed state JSON

        Raises:
            TerraformStateError: If terraform command fails
        """
        try:
            result = subprocess.run(
                ["terraform", "show", "-json"],
                cwd=self.state_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            return json.loads(result.stdout)

        except subprocess.CalledProcessError as e:
            raise TerraformStateError(f"terraform show command failed: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise TerraformStateError(f"Invalid JSON in Terraform state: {e}") from e
        except FileNotFoundError:
            raise TerraformStateError(
                "terraform command not found - ensure Terraform CLI is installed"
            )

    def _parse_resources(self, state_data: dict) -> List[TerraformResource]:
        """
        Parse resources from Terraform state JSON.

        Args:
            state_data: Terraform state as dictionary

        Returns:
            List of TerraformResource objects
        """
        resources = []

        root_module = state_data.get("values", {}).get("root_module", {})
        resource_list = root_module.get("resources", [])

        for resource in resource_list:
            try:
                tf_resource = TerraformResource(
                    type=resource.get("type", "unknown"),
                    name=resource.get("name", "unnamed"),
                    address=resource.get("address", ""),
                    values=resource.get("values", {}),
                    depends_on=resource.get("depends_on", []),
                )
                resources.append(tf_resource)
                logger.debug(
                    "Parsed Terraform resource",
                    type=tf_resource.type,
                    name=tf_resource.name,
                    address=tf_resource.address,
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse Terraform resource",
                    resource_address=resource.get("address"),
                    error=str(e),
                )
                continue

        return resources

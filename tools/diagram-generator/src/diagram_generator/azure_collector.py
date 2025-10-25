"""
Azure Resource Graph collection module.

Queries Azure Resource Graph for infrastructure resources and relationships.
"""

from typing import List, Optional

from azure.core.exceptions import AzureError
from azure.identity import (
    AzureCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
)
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

from diagram_generator.exceptions import AzureAPIError, AuthenticationError
from diagram_generator.models import AzureAuthMethod, AzureResource
from diagram_generator.utils import get_logger, retry_on_exception

logger = get_logger(__name__)


class AzureResourceGraphCollector:
    """Collects and parses Azure resources via Resource Graph API."""

    def __init__(
        self,
        subscription_id: str,
        auth_method: AzureAuthMethod = AzureAuthMethod.AZURE_CLI,
    ):
        """
        Initialize Azure Resource Graph collector.

        Args:
            subscription_id: Azure subscription ID to query
            auth_method: Authentication method to use

        Raises:
            AuthenticationError: If Azure authentication fails
        """
        self.subscription_id = subscription_id
        self.auth_method = auth_method
        self.client = self._initialize_client()
        logger.info(
            "Azure collector initialized",
            subscription_id=subscription_id,
            auth_method=auth_method.value,
        )

    def _initialize_client(self) -> ResourceGraphClient:
        """
        Initialize Azure Resource Graph client with appropriate credentials.

        Returns:
            Configured ResourceGraphClient

        Raises:
            AuthenticationError: If credential initialization fails
        """
        try:
            if self.auth_method == AzureAuthMethod.AZURE_CLI:
                credential = AzureCliCredential()
            elif self.auth_method == AzureAuthMethod.MANAGED_IDENTITY:
                credential = ManagedIdentityCredential()
            else:  # SERVICE_PRINCIPAL or default
                credential = DefaultAzureCredential()

            return ResourceGraphClient(credential=credential)

        except Exception as e:
            logger.error("Failed to initialize Azure credentials", error=str(e))
            raise AuthenticationError(f"Azure authentication failed: {e}") from e

    @retry_on_exception(max_attempts=3, delay=2.0, exceptions=(AzureError,))
    def collect_resources(self, resource_types: Optional[List[str]] = None) -> List[AzureResource]:
        """
        Collect Azure resources from Resource Graph.

        Args:
            resource_types: Optional list of resource types to filter (e.g., ['Microsoft.Network/virtualNetworks'])

        Returns:
            List of Azure resources

        Raises:
            AzureAPIError: If Resource Graph query fails
        """
        logger.info("Collecting Azure resources", resource_types=resource_types)

        try:
            query = self._build_query(resource_types)
            result = self._execute_query(query)
            resources = self._parse_resources(result)
            logger.info("Azure resources collected", count=len(resources))
            return resources

        except Exception as e:
            logger.error("Failed to collect Azure resources", error=str(e))
            raise AzureAPIError(f"Failed to collect Azure resources: {e}") from e

    def _build_query(self, resource_types: Optional[List[str]] = None) -> str:
        """
        Build KQL query for Resource Graph.

        Args:
            resource_types: Optional list of resource types to filter

        Returns:
            KQL query string
        """
        base_query = """
        Resources
        | where subscriptionId == '{subscription_id}'
        | project
            id,
            name,
            type,
            location,
            resourceGroup,
            tags,
            properties
        """

        query = base_query.format(subscription_id=self.subscription_id)

        if resource_types:
            types_filter = "', '".join(resource_types)
            query += f"\n| where type in ('{types_filter}')"

        return query

    def _execute_query(self, query: str) -> dict:
        """
        Execute KQL query against Resource Graph.

        Args:
            query: KQL query string

        Returns:
            Query results as dictionary

        Raises:
            AzureError: If query execution fails
        """
        request = QueryRequest(
            subscriptions=[self.subscription_id],
            query=query,
            options=QueryRequestOptions(
                result_format="objectArray",
            ),
        )

        logger.debug("Executing Resource Graph query", query=query)
        response = self.client.resources(request)

        return {
            "data": response.data,
            "total_records": response.total_records,
            "count": response.count,
        }

    def _parse_resources(self, result: dict) -> List[AzureResource]:
        """
        Parse Resource Graph results into AzureResource objects.

        Args:
            result: Query result dictionary

        Returns:
            List of AzureResource objects
        """
        resources = []

        for resource in result.get("data", []):
            try:
                # Extract resource group from id
                resource_id = resource.get("id", "")
                resource_group = self._extract_resource_group(resource_id)

                azure_resource = AzureResource(
                    id=resource_id,
                    name=resource.get("name", "unnamed"),
                    type=resource.get("type", "unknown"),
                    location=resource.get("location", "unknown"),
                    resource_group=resource_group,
                    tags=resource.get("tags", {}),
                    properties=resource.get("properties", {}),
                )
                resources.append(azure_resource)
                logger.debug(
                    "Parsed Azure resource",
                    type=azure_resource.type,
                    name=azure_resource.name,
                    id=azure_resource.id,
                )

            except Exception as e:
                logger.warning(
                    "Failed to parse Azure resource",
                    resource_id=resource.get("id"),
                    error=str(e),
                )
                continue

        return resources

    def _extract_resource_group(self, resource_id: str) -> str:
        """
        Extract resource group name from Azure resource ID.

        Args:
            resource_id: Full Azure resource ID

        Returns:
            Resource group name
        """
        # Azure resource ID format:
        # /subscriptions/{subscription}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups")
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            logger.warning("Could not extract resource group from ID", resource_id=resource_id)
            return "unknown"

    def collect_network_resources(self) -> List[AzureResource]:
        """
        Collect network-specific Azure resources.

        Returns:
            List of network resources (VNets, subnets, NSGs, load balancers, etc.)
        """
        network_types = [
            "Microsoft.Network/virtualNetworks",
            "Microsoft.Network/networkSecurityGroups",
            "Microsoft.Network/loadBalancers",
            "Microsoft.Network/publicIPAddresses",
            "Microsoft.Network/networkInterfaces",
            "Microsoft.Network/routeTables",
            "Microsoft.Network/virtualNetworkGateways",
        ]
        return self.collect_resources(resource_types=network_types)

    def collect_compute_resources(self) -> List[AzureResource]:
        """
        Collect compute-specific Azure resources.

        Returns:
            List of compute resources (VMs, scale sets, etc.)
        """
        compute_types = [
            "Microsoft.Compute/virtualMachines",
            "Microsoft.Compute/virtualMachineScaleSets",
            "Microsoft.Compute/disks",
        ]
        return self.collect_resources(resource_types=compute_types)

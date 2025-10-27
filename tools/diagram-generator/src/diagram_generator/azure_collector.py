"""
Azure Resource Graph collection module.

Queries Azure Resource Graph for infrastructure resources and relationships.
"""

from typing import Any, Optional

from azure.core.exceptions import AzureError
from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

from diagram_generator.exceptions import AuthenticationError, AzureAPIError
from diagram_generator.models import AzureAuthMethod, AzureResource
from diagram_generator.utils import get_logger, retry_on_exception

logger = get_logger(__name__)


class AzureResourceGraphCollector:
    """Collects and parses Azure resources via Resource Graph API."""

    def __init__(
        self,
        subscription_id: str,
        auth_method: AzureAuthMethod = AzureAuthMethod.AZURE_CLI,
        resource_groups: Optional[list[str]] = None,
    ):
        """
        Initialize Azure Resource Graph collector.

        Args:
            subscription_id: Azure subscription ID to query
            auth_method: Authentication method to use
            resource_groups: Optional list of resource groups to filter queries (improves performance)

        Raises:
            AuthenticationError: If Azure authentication fails
        """
        self.subscription_id = subscription_id
        self.auth_method = auth_method
        self.resource_groups = resource_groups or []
        self.client = self._initialize_client()
        logger.info(
            "Azure collector initialized",
            subscription_id=subscription_id,
            auth_method=auth_method.value,
            resource_groups=self.resource_groups,
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
    def collect_resources(self, resource_types: Optional[list[str]] = None) -> list[AzureResource]:
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

    def _build_query(self, resource_types: Optional[list[str]] = None) -> str:
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

        # Add resource group filter if specified (improves performance)
        if self.resource_groups:
            rg_filter = "', '".join(self.resource_groups)
            query += f"\n| where resourceGroup in ('{rg_filter}')"

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

    def _parse_resources(self, result: dict) -> list[AzureResource]:
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

    def collect_network_resources(self) -> list[AzureResource]:
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

    def collect_compute_resources(self) -> list[AzureResource]:
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

    def collect_load_balancer_relationships(self) -> dict[str, Any]:
        """
        Collect load balancer backend pool and frontend IP relationships.

        Returns:
            Dictionary mapping LB resource IDs to their backend targets and frontend configs
        """
        logger.info("Collecting load balancer relationships")

        query = f"""
        Resources
        | where subscriptionId == '{self.subscription_id}'
        | where type == 'microsoft.network/loadbalancers'
        """

        # Add resource group filter if specified
        if self.resource_groups:
            rg_filter = "', '".join(self.resource_groups)
            query += f"\n        | where resourceGroup in ('{rg_filter}')"

        query += """
        | extend backendPools = properties.backendAddressPools
        | extend frontendConfigs = properties.frontendIPConfigurations
        | extend probes = properties.probes
        | project id, name, backendPools, frontendConfigs, probes, properties
        """

        try:
            result = self._execute_query(query)
            relationships = {}

            for lb in result.get("data", []):
                lb_id = lb.get("id", "")
                backend_pools = lb.get("backendPools", [])
                frontend_configs = lb.get("frontendConfigs", [])

                # Extract backend target IPs/NICs
                backend_targets = []
                for pool in backend_pools:
                    if isinstance(pool, dict):
                        pool_props = pool.get("properties", {})
                        # Backend addresses can be NICs or IP addresses
                        backend_ips = pool_props.get("backendIPConfigurations", [])
                        for ip_config in backend_ips:
                            if isinstance(ip_config, dict):
                                target_id = ip_config.get("id", "")
                                if target_id:
                                    backend_targets.append(target_id)

                # Extract frontend IPs (for inbound traffic identification)
                frontend_ips = []
                for frontend in frontend_configs:
                    if isinstance(frontend, dict):
                        frontend_props = frontend.get("properties", {})
                        subnet_id = frontend_props.get("subnet", {}).get("id", "")
                        public_ip_id = frontend_props.get("publicIPAddress", {}).get("id", "")
                        if subnet_id:
                            frontend_ips.append({"type": "internal", "subnet_id": subnet_id})
                        if public_ip_id:
                            frontend_ips.append({"type": "public", "public_ip_id": public_ip_id})

                relationships[lb_id] = {
                    "name": lb.get("name", ""),
                    "backend_targets": backend_targets,
                    "frontend_configs": frontend_ips,
                    "is_public": any(fe["type"] == "public" for fe in frontend_ips),
                }

            logger.info(
                "Load balancer relationships collected",
                count=len(relationships),
            )
            return relationships

        except Exception as e:
            logger.error("Failed to collect LB relationships", error=str(e))
            return {}

    def collect_route_table_relationships(self) -> dict[str, Any]:
        """
        Collect route table next-hop relationships for traffic flow detection.

        Returns:
            Dictionary mapping route table IDs to their next-hop configurations
        """
        logger.info("Collecting route table relationships")

        query = f"""
        Resources
        | where subscriptionId == '{self.subscription_id}'
        | where type == 'microsoft.network/routetables'
        """

        # Add resource group filter if specified
        if self.resource_groups:
            rg_filter = "', '".join(self.resource_groups)
            query += f"\n        | where resourceGroup in ('{rg_filter}')"

        query += """
        | extend routes = properties.routes
        | extend subnets = properties.subnets
        | project id, name, routes, subnets, properties
        """

        try:
            result = self._execute_query(query)
            relationships = {}

            for rt in result.get("data", []):
                rt_id = rt.get("id", "")
                routes = rt.get("routes", [])
                subnets = rt.get("subnets", [])

                # Extract next-hop information
                next_hops = []
                for route in routes:
                    if isinstance(route, dict):
                        route_props = route.get("properties", {})
                        next_hop_type = route_props.get("nextHopType", "")
                        next_hop_ip = route_props.get("nextHopIpAddress", "")
                        address_prefix = route_props.get("addressPrefix", "")

                        if next_hop_type or next_hop_ip:
                            next_hops.append(
                                {
                                    "type": next_hop_type,
                                    "ip": next_hop_ip,
                                    "prefix": address_prefix,
                                }
                            )

                # Extract associated subnets
                associated_subnets = []
                for subnet in subnets:
                    if isinstance(subnet, dict):
                        subnet_id = subnet.get("id", "")
                        if subnet_id:
                            associated_subnets.append(subnet_id)

                relationships[rt_id] = {
                    "name": rt.get("name", ""),
                    "next_hops": next_hops,
                    "associated_subnets": associated_subnets,
                }

            logger.info(
                "Route table relationships collected",
                count=len(relationships),
            )
            return relationships

        except Exception as e:
            logger.error("Failed to collect route table relationships", error=str(e))
            return {}

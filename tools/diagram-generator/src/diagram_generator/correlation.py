"""
Resource correlation engine.

Cross-references resources from Terraform, Azure, and F5 XC to build
unified infrastructure graph with relationships and drift detection.
"""

from typing import Any

import networkx as nx

from diagram_generator.exceptions import CorrelationError
from diagram_generator.models import (
    AzureResource,
    ConfigurationDrift,
    CorrelatedResources,
    F5XCResource,
    RelationshipType,
    ResourceRelationship,
    TerraformResource,
)
from diagram_generator.utils import extract_ip_addresses, get_logger, sanitize_resource_id

logger = get_logger(__name__)


class ResourceCorrelator:
    """Correlates resources across Terraform, Azure, and F5 XC."""

    def __init__(
        self,
        match_by_tags: bool = True,
        match_by_ip: bool = True,
        enable_drift_detection: bool = True,
    ):
        """
        Initialize resource correlator.

        Args:
            match_by_tags: Enable tag/label-based correlation
            match_by_ip: Enable IP address-based correlation
            enable_drift_detection: Enable configuration drift detection
        """
        self.match_by_tags = match_by_tags
        self.match_by_ip = match_by_ip
        self.enable_drift_detection = enable_drift_detection
        self.graph = nx.DiGraph()

        logger.info(
            "Resource correlator initialized",
            match_by_tags=match_by_tags,
            match_by_ip=match_by_ip,
            drift_detection=enable_drift_detection,
        )

    def correlate(
        self,
        terraform_resources: list[TerraformResource],
        azure_resources: list[AzureResource],
        f5xc_resources: list[F5XCResource],
    ) -> CorrelatedResources:
        """
        Correlate resources from all three sources.

        Args:
            terraform_resources: Resources from Terraform state
            azure_resources: Resources from Azure Resource Graph
            f5xc_resources: Resources from F5 XC API

        Returns:
            Correlated resources with relationships and drift

        Raises:
            CorrelationError: If correlation process fails
        """
        logger.info(
            "Starting resource correlation",
            terraform_count=len(terraform_resources),
            azure_count=len(azure_resources),
            f5xc_count=len(f5xc_resources),
        )

        try:
            # Build graph with all resources
            self._add_resources_to_graph(terraform_resources, azure_resources, f5xc_resources)

            # Establish relationships
            relationships = []
            relationships.extend(self._correlate_terraform_dependencies(terraform_resources))
            relationships.extend(
                self._correlate_terraform_to_azure(terraform_resources, azure_resources)
            )
            relationships.extend(self._correlate_f5xc_to_azure(f5xc_resources, azure_resources))
            relationships.extend(
                self._correlate_by_tags(terraform_resources, azure_resources, f5xc_resources)
            )
            relationships.extend(self._correlate_by_ip(f5xc_resources, azure_resources))

            # Detect drift
            drift = []
            if self.enable_drift_detection:
                drift = self._detect_drift(terraform_resources, azure_resources)

            # Build result
            all_resources = [r.model_dump() for r in terraform_resources]
            all_resources.extend([r.model_dump() for r in azure_resources])
            all_resources.extend([r.model_dump() for r in f5xc_resources])

            result = CorrelatedResources(
                resources=all_resources,
                relationships=relationships,
                drift=drift,
            )

            logger.info(
                "Resource correlation completed",
                total_resources=len(all_resources),
                relationships=len(relationships),
                drift_issues=len(drift),
            )

            return result

        except Exception as e:
            logger.error("Resource correlation failed", error=str(e))
            raise CorrelationError(f"Failed to correlate resources: {e}") from e

    def _add_resources_to_graph(
        self,
        terraform_resources: list[TerraformResource],
        azure_resources: list[AzureResource],
        f5xc_resources: list[F5XCResource],
    ) -> None:
        """Add all resources as nodes in the graph."""
        # Add Terraform resources
        for resource in terraform_resources:
            node_id = sanitize_resource_id(resource.address)
            self.graph.add_node(node_id, resource=resource, source="terraform")

        # Add Azure resources
        for azure_resource in azure_resources:
            node_id = sanitize_resource_id(azure_resource.id)
            self.graph.add_node(node_id, resource=azure_resource, source="azure")

        # Add F5 XC resources
        for f5xc_resource in f5xc_resources:
            node_id = sanitize_resource_id(
                f"{f5xc_resource.namespace}/{f5xc_resource.type}/{f5xc_resource.name}"
            )
            self.graph.add_node(node_id, resource=f5xc_resource, source="f5xc")

        logger.info("Added resources to graph", node_count=self.graph.number_of_nodes())

    def _correlate_terraform_dependencies(
        self, terraform_resources: list[TerraformResource]
    ) -> list[ResourceRelationship]:
        """
        Create relationships based on Terraform dependencies.

        Args:
            terraform_resources: Terraform resources with depends_on

        Returns:
            List of dependency relationships
        """
        relationships = []

        for resource in terraform_resources:
            source_id = sanitize_resource_id(resource.address)

            for dependency in resource.depends_on:
                target_id = sanitize_resource_id(dependency)

                relationship = ResourceRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=RelationshipType.TERRAFORM_DEPENDENCY,
                    metadata={"depends_on": dependency},
                )
                relationships.append(relationship)

                # Add edge to graph
                if target_id in self.graph:
                    self.graph.add_edge(source_id, target_id, relationship=relationship)

        logger.debug("Terraform dependencies correlated", count=len(relationships))
        return relationships

    def _correlate_terraform_to_azure(
        self, terraform_resources: list[TerraformResource], azure_resources: list[AzureResource]
    ) -> list[ResourceRelationship]:
        """
        Correlate Terraform resources to Azure resources by resource ID.

        Args:
            terraform_resources: Terraform resources
            azure_resources: Azure resources

        Returns:
            List of Terraform-Azure relationships
        """
        relationships = []

        # Build Azure resource ID lookup
        azure_lookup = {resource.id.lower(): resource for resource in azure_resources}

        for tf_resource in terraform_resources:
            # Check if Terraform resource has Azure resource ID
            azure_id = tf_resource.values.get("id", "").lower()

            if azure_id and azure_id in azure_lookup:
                azure_resource = azure_lookup[azure_id]

                source_id = sanitize_resource_id(tf_resource.address)
                target_id = sanitize_resource_id(azure_resource.id)

                relationship = ResourceRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=RelationshipType.TERRAFORM_AZURE,
                    metadata={
                        "azure_id": azure_id,
                        "terraform_type": tf_resource.type,
                        "azure_type": azure_resource.type,
                    },
                )
                relationships.append(relationship)

                # Add edge to graph
                if target_id in self.graph:
                    self.graph.add_edge(source_id, target_id, relationship=relationship)

        logger.debug("Terraform-Azure correlation completed", count=len(relationships))
        return relationships

    def _correlate_f5xc_to_azure(
        self, f5xc_resources: list[F5XCResource], azure_resources: list[AzureResource]
    ) -> list[ResourceRelationship]:
        """
        Correlate F5 XC resources to Azure resources.

        Matches:
        - F5 XC origin pools to Azure VMs (by IP or FQDN)
        - F5 XC sites to Azure VNets (by network configuration)

        Args:
            f5xc_resources: F5 XC resources
            azure_resources: Azure resources

        Returns:
            List of F5 XC-Azure relationships
        """
        relationships = []

        # Build Azure VM and VNet lookups
        azure_vms = [r for r in azure_resources if r.type == "Microsoft.Compute/virtualMachines"]
        azure_vnets = [r for r in azure_resources if r.type == "Microsoft.Network/virtualNetworks"]

        # Correlate origin pools to VMs
        for f5xc_resource in f5xc_resources:
            if f5xc_resource.type == "origin_pool":
                relationships.extend(self._match_origin_pool_to_vms(f5xc_resource, azure_vms))
            elif f5xc_resource.type == "site":
                relationships.extend(self._match_site_to_vnets(f5xc_resource, azure_vnets))

        logger.debug("F5 XC-Azure correlation completed", count=len(relationships))
        return relationships

    def _match_origin_pool_to_vms(
        self, origin_pool: F5XCResource, azure_vms: list[AzureResource]
    ) -> list[ResourceRelationship]:
        """Match F5 XC origin pool to Azure VMs."""
        relationships = []

        # Extract origin IPs from pool spec
        origins = origin_pool.spec.get("origin_servers", [])
        origin_ips = set()

        for origin in origins:
            # Extract IP addresses from origin configuration
            if "public_ip" in origin:
                origin_ips.add(origin["public_ip"].get("ip", ""))
            elif "private_ip" in origin:
                origin_ips.add(origin["private_ip"].get("ip", ""))

        # Match to Azure VMs
        for vm in azure_vms:
            vm_ips = set(extract_ip_addresses(vm.properties))

            if origin_ips & vm_ips:  # Intersection
                source_id = sanitize_resource_id(
                    f"{origin_pool.namespace}/{origin_pool.type}/{origin_pool.name}"
                )
                target_id = sanitize_resource_id(vm.id)

                relationship = ResourceRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=RelationshipType.F5XC_ORIGIN_TO_AZURE_VM,
                    metadata={
                        "matched_ips": list(origin_ips & vm_ips),
                        "origin_pool": origin_pool.name,
                        "vm_name": vm.name,
                    },
                )
                relationships.append(relationship)

                # Add edge to graph
                if target_id in self.graph:
                    self.graph.add_edge(source_id, target_id, relationship=relationship)

        return relationships

    def _match_site_to_vnets(
        self, site: F5XCResource, azure_vnets: list[AzureResource]
    ) -> list[ResourceRelationship]:
        """Match F5 XC site to Azure VNets."""
        relationships = []

        # Extract site network configuration
        site.spec.get("network", {})

        # Match based on network properties (simplified)
        for vnet in azure_vnets:
            # This is a simplified matching logic
            # In production, you'd want more sophisticated network matching
            vnet_name = vnet.name.lower()
            site_name = site.name.lower()

            # Check if names suggest a relationship
            if vnet_name in site_name or site_name in vnet_name:
                source_id = sanitize_resource_id(f"{site.namespace}/{site.type}/{site.name}")
                target_id = sanitize_resource_id(vnet.id)

                relationship = ResourceRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=RelationshipType.F5XC_SITE_TO_AZURE_VNET,
                    metadata={
                        "site_name": site.name,
                        "vnet_name": vnet.name,
                        "match_method": "name_similarity",
                    },
                )
                relationships.append(relationship)

                # Add edge to graph
                if target_id in self.graph:
                    self.graph.add_edge(source_id, target_id, relationship=relationship)

        return relationships

    def _correlate_by_tags(
        self,
        terraform_resources: list[TerraformResource],
        azure_resources: list[AzureResource],
        f5xc_resources: list[F5XCResource],
    ) -> list[ResourceRelationship]:
        """
        Correlate resources by matching tags/labels.

        Args:
            terraform_resources: Terraform resources
            azure_resources: Azure resources
            f5xc_resources: F5 XC resources

        Returns:
            List of tag-based relationships
        """
        if not self.match_by_tags:
            return []

        relationships = []

        # Build tag indexes
        tf_by_tag = self._index_resources_by_tags(terraform_resources, "terraform")
        azure_by_tag = self._index_resources_by_tags(azure_resources, "azure")
        f5xc_by_tag = self._index_resources_by_tags(f5xc_resources, "f5xc")

        # Find matching tags
        all_tags = set(tf_by_tag.keys()) | set(azure_by_tag.keys()) | set(f5xc_by_tag.keys())

        for tag_key, tag_value in all_tags:
            # Find resources with matching tags
            tf_matches = tf_by_tag.get((tag_key, tag_value), [])
            azure_matches = azure_by_tag.get((tag_key, tag_value), [])
            f5xc_by_tag.get((tag_key, tag_value), [])

            # Create relationships between matching resources
            for tf_res in tf_matches:
                for azure_res in azure_matches:
                    relationship = ResourceRelationship(
                        source_id=tf_res,
                        target_id=azure_res,
                        relationship_type=RelationshipType.GENERIC_DEPENDENCY,
                        metadata={"tag_key": tag_key, "tag_value": tag_value},
                    )
                    relationships.append(relationship)

        logger.debug("Tag-based correlation completed", count=len(relationships))
        return relationships

    def _correlate_by_ip(
        self, _f5xc_resources: list[F5XCResource], _azure_resources: list[AzureResource]
    ) -> list[ResourceRelationship]:
        """
        Correlate resources by IP address matching.

        Args:
            _f5xc_resources: F5 XC resources (unused - placeholder for future implementation)
            _azure_resources: Azure resources (unused - placeholder for future implementation)

        Returns:
            List of IP-based relationships
        """
        if not self.match_by_ip:
            return []

        # This is handled in _correlate_f5xc_to_azure
        # Kept as separate method for extensibility
        return []

    def _index_resources_by_tags(
        self, resources: list[Any], source: str
    ) -> dict[tuple[str, str], list[str]]:
        """
        Build index of resources by their tags.

        Args:
            resources: Resources to index
            source: Resource source (terraform, azure, f5xc)

        Returns:
            Dictionary mapping (tag_key, tag_value) to resource IDs
        """
        tag_index: dict[tuple[str, str], list[str]] = {}

        for resource in resources:
            # Get resource ID
            if source == "terraform":
                resource_id = sanitize_resource_id(resource.address)
                tags = resource.values.get("tags", {})
            elif source == "azure":
                resource_id = sanitize_resource_id(resource.id)
                tags = resource.tags
            elif source == "f5xc":
                resource_id = sanitize_resource_id(
                    f"{resource.namespace}/{resource.type}/{resource.name}"
                )
                tags = resource.metadata.get("labels", {})
            else:
                continue

            # Index by tags
            for key, value in tags.items():
                tag_tuple = (key, value)
                if tag_tuple not in tag_index:
                    tag_index[tag_tuple] = []
                tag_index[tag_tuple].append(resource_id)

        return tag_index

    def _detect_drift(
        self, terraform_resources: list[TerraformResource], azure_resources: list[AzureResource]
    ) -> list[ConfigurationDrift]:
        """
        Detect configuration drift between Terraform and Azure.

        Args:
            terraform_resources: Resources from Terraform state
            azure_resources: Resources from Azure

        Returns:
            List of detected drift
        """
        drift_list = []

        # Build Azure lookup by ID
        azure_lookup = {resource.id.lower(): resource for resource in azure_resources}

        for tf_resource in terraform_resources:
            azure_id = tf_resource.values.get("id", "").lower()

            if azure_id and azure_id in azure_lookup:
                azure_resource = azure_lookup[azure_id]

                # Check for tag drift
                tf_tags = tf_resource.values.get("tags", {})
                azure_tags = azure_resource.tags

                if tf_tags != azure_tags:
                    drift = ConfigurationDrift(
                        resource_address=tf_resource.address,
                        drift_type="tags",
                        terraform_value=tf_tags,
                        azure_value=azure_tags,
                        details=f"Tag mismatch for {tf_resource.name}",
                    )
                    drift_list.append(drift)

                # Check for location drift
                tf_location = tf_resource.values.get("location", "").lower()
                azure_location = azure_resource.location.lower()

                if tf_location and tf_location != azure_location:
                    drift = ConfigurationDrift(
                        resource_address=tf_resource.address,
                        drift_type="location",
                        terraform_value=tf_location,
                        azure_value=azure_location,
                        details=f"Location mismatch for {tf_resource.name}",
                    )
                    drift_list.append(drift)

        logger.info("Drift detection completed", drift_count=len(drift_list))
        return drift_list

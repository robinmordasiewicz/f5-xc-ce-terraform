"""
Draw.io diagram generation module.

Converts correlated resources into draw.io (diagrams.net) mxGraph XML format.
"""

import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional
from xml.dom import minidom

from diagram_generator.exceptions import DiagramGenerationError
from diagram_generator.models import CorrelatedResources, DrawioDocument, ResourceSource
from diagram_generator.utils import format_resource_label, get_logger, get_resource_short_name

logger = get_logger(__name__)


class DrawioDiagramGenerator:
    """Generates draw.io (mxGraph XML) diagrams from correlated resources."""

    # Shape colors by resource source
    SOURCE_COLORS = {
        ResourceSource.TERRAFORM: "#FF6B6B",  # Red
        ResourceSource.AZURE: "#4A90E2",  # Blue
        ResourceSource.F5XC: "#50C878",  # Green
    }

    # Azure official color palette (matching Microsoft Learn diagrams)
    AZURE_COLORS = {
        "vnet": "#0078D4",  # Azure blue for VNets
        "subnet": "#C7E0F4",  # Light blue for subnets
        "gateway": "#FF6C37",  # Orange for gateways
        "nva": "#00A4EF",  # Cyan for NVAs
        "vm": "#0078D4",  # Azure blue for VMs
        "lb": "#00BCF2",  # Light blue for load balancers
        "nsg": "#FF8C00",  # Dark orange for NSGs
    }

    # Azure resource shapes using Draw.io Azure stencil library
    AZURE_SHAPE_STYLES = {
        # VNet containers - dashed border like Microsoft Learn
        "vnet": "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#0078D4;strokeWidth=2;fontSize=12;fontStyle=1;dashed=1;dashPattern=5 5;",
        "subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=10;verticalAlign=top;",
        "gateway_subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=10;verticalAlign=top;",
        "nva_subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=10;verticalAlign=top;",
        # Azure resource icons
        "vm": "shape=mxgraph.azure.virtual_machine;fillColor=#0078D4;strokeColor=#005A9E;strokeWidth=1;",
        "lb": "shape=mxgraph.azure.load_balancer;fillColor=#00BCF2;strokeColor=#0078D4;strokeWidth=1;",
        "gateway": "shape=mxgraph.azure.virtual_network_gateway;fillColor=#FF6C37;strokeColor=#CC5529;strokeWidth=1;",
        "nsg": "shape=mxgraph.azure.network_security_group;fillColor=#FF8C00;strokeColor=#CC7000;strokeWidth=1;",
        "nic": "shape=mxgraph.azure.network_interface_card;fillColor=#0078D4;strokeColor=#005A9E;strokeWidth=1;",
        "pip": "shape=mxgraph.azure.public_ip;fillColor=#00BCF2;strokeColor=#0078D4;strokeWidth=1;",
        # Special elements matching Microsoft Learn
        "internet_cloud": "ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#5D9CEC;strokeColor=#FFFFFF;strokeWidth=2;fontColor=#FFFFFF;fontSize=14;fontStyle=1;",
        "onpremises_building": "shape=mxgraph.azure.building;fillColor=#0078D4;strokeColor=#005A9E;strokeWidth=1;",
        "route_table": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=9;align=left;verticalAlign=top;",
        "sequence_number": "ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#107C10;strokeColor=#FFFFFF;strokeWidth=2;fontColor=#FFFFFF;fontSize=12;fontStyle=1;",
        "f5xc_site": "shape=cloud;fillColor=#50C878;strokeColor=#2E7D54;strokeWidth=2;",
        "default": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F4F8;strokeColor=#0078D4;strokeWidth=1;",
    }

    # Traffic flow arrow styles (matching Microsoft Learn)
    TRAFFIC_FLOW_STYLES = {
        "inbound": "endArrow=classic;html=1;strokeColor=#4472C4;strokeWidth=3;",  # Inbound traffic (blue)
        "return": "endArrow=classic;html=1;strokeColor=#70AD47;strokeWidth=3;",  # Return traffic (green)
        "north_south": "endArrow=classic;html=1;strokeColor=#4472C4;strokeWidth=3;",  # Internet traffic (blue)
        "east_west": "endArrow=classic;html=1;strokeColor=#70AD47;strokeWidth=3;",  # Internal traffic (green)
        "peering": "endArrow=classic;html=1;strokeColor=#666666;strokeWidth=2;dashed=1;",  # VNet peering
        "gateway_connection": "endArrow=classic;html=1;strokeColor=#4472C4;strokeWidth=3;",  # Gateway traffic
        "nva_traffic": "endArrow=classic;html=1;strokeColor=#70AD47;strokeWidth=3;",  # Through NVA
        "dependency": "endArrow=classic;html=1;strokeColor=#666666;strokeWidth=2;dashed=1;",  # Generic dependency
    }

    def __init__(
        self,
        title: str = "Azure + F5 XC Infrastructure",
        auto_layout: bool = True,
        group_by_platform: bool = True,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize draw.io diagram generator.

        Args:
            title: Diagram title
            auto_layout: Enable automatic layout (hierarchical)
            group_by_platform: Group resources by platform (Terraform/Azure/F5 XC)
            output_dir: Output directory for diagram files (default: current directory)
        """
        self.title = title
        self.auto_layout = auto_layout
        self.group_by_platform = group_by_platform
        self.output_dir = output_dir or Path.cwd()

        # Layout configuration
        self.layout = {
            "page_width": 1600,
            "page_height": 1200,
            "shape_width": 160,
            "shape_height": 80,
            "horizontal_spacing": 200,
            "vertical_spacing": 120,
            "group_padding": 40,
        }

        logger.info(
            "Draw.io diagram generator initialized",
            title=title,
            auto_layout=auto_layout,
            output_dir=str(self.output_dir),
        )

    def generate(self, correlated_resources: CorrelatedResources) -> DrawioDocument:
        """
        Generate draw.io diagram from correlated resources.

        Args:
            correlated_resources: Correlated infrastructure resources

        Returns:
            DrawioDocument with file path

        Raises:
            DiagramGenerationError: If diagram generation fails
        """
        logger.info(
            "Generating draw.io diagram",
            resource_count=len(correlated_resources.resources),
            relationship_count=len(correlated_resources.relationships),
        )

        try:
            # Create mxGraph XML structure
            diagram_xml = self._create_diagram_xml(correlated_resources)

            # Save to file
            output_file = self._save_diagram(diagram_xml)

            # Export to PNG
            png_file = self._export_to_png(output_file)

            logger.info(
                "Draw.io diagram generated successfully",
                file_path=str(output_file),
                image_file_path=str(png_file),
            )

            return DrawioDocument(
                file_path=output_file,
                image_file_path=png_file,
                title=self.title,
            )

        except Exception as e:
            logger.error("Draw.io diagram generation failed", error=str(e))
            raise DiagramGenerationError(f"Failed to generate draw.io diagram: {e}") from e

    def _create_diagram_xml(self, correlated_resources: CorrelatedResources) -> ET.Element:
        """Create mxGraph XML structure."""
        # Root mxfile element
        mxfile = ET.Element("mxfile", host="app.diagrams.net", type="device")

        # Diagram element
        diagram = ET.SubElement(
            mxfile,
            "diagram",
            id=str(uuid.uuid4()),
            name=self.title,
        )

        # mxGraphModel
        graph_model = ET.SubElement(
            diagram,
            "mxGraphModel",
            dx="1434",
            dy="796",
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(self.layout["page_width"]),
            pageHeight=str(self.layout["page_height"]),
            math="0",
            shadow="0",
        )

        # Root element
        root = ET.SubElement(graph_model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")

        # Generate shapes and get content height
        shapes, max_content_height = self._generate_shapes(root, correlated_resources.resources)

        # Generate connections
        self._generate_connections(root, correlated_resources.relationships, shapes)

        # Add Microsoft Learn styling elements
        cell_id = len(root) + 1

        # Add Internet cloud at the top (always above first content)
        cell_id = self._add_internet_cloud(root, cell_id)

        # Add traffic flow legend at the bottom (below all content with margin)
        legend_y_position = max_content_height + 50
        cell_id = self._add_traffic_legend(root, cell_id, y_position=legend_y_position)

        # Add Microsoft Azure branding (next to last VNet, bottom-right area)
        branding_y = max(max_content_height - 200, 100)  # Position near bottom content
        cell_id = self._add_azure_branding(root, cell_id, y_position=branding_y)

        # Add sequence indicators at meaningful positions relative to first VNet
        first_vnet_y = 120  # Just below Internet cloud
        sequence_positions = [
            (650, first_vnet_y + 10, "1"),  # Internet → VNet entry
            (650, first_vnet_y + 130, "2"),  # Within VNet
            (750, first_vnet_y + 130, "3"),  # Processing
            (850, first_vnet_y + 130, "4"),  # Exit/routing
        ]
        cell_id = self._add_sequence_indicators(root, cell_id, sequence_positions)

        logger.info(
            "Added Microsoft Learn styling elements to diagram", content_height=max_content_height
        )

        return mxfile

    def _generate_shapes(
        self, root: ET.Element, resources: list[Any]
    ) -> tuple[dict[str, str], int]:
        """
        Generate hierarchical mxGraph shapes for resources.

        Creates structure: Platform → VNet → Subnet → Resources
        Matches Microsoft Learn diagram style with proper nesting.

        Returns:
            Tuple of (shape_id_map, max_content_height)
        """
        shapes = {}
        cell_id_counter = 2  # Start after default cells (0 and 1)
        max_content_height = 0  # Track maximum Y coordinate for positioning legend/branding

        # Group resources for hierarchical layout
        if self.group_by_platform:
            platform_groups = self._group_resources_by_platform(resources)
            x_offset = 50

            for platform, platform_resources in platform_groups.items():
                if platform == "Azure":
                    # Azure gets hierarchical VNet/Subnet structure
                    cell_id_counter, platform_shapes, content_height = self._create_azure_hierarchy(
                        root, platform_resources, x_offset, cell_id_counter
                    )
                    shapes.update(platform_shapes)
                    max_content_height = max(max_content_height, content_height)
                    x_offset += 900  # Wider for hierarchical structure

                elif platform == "F5 XC":
                    # F5 XC gets grouped structure
                    cell_id_counter, f5xc_shapes, content_height = self._create_f5xc_group(
                        root, platform_resources, x_offset, cell_id_counter
                    )
                    shapes.update(f5xc_shapes)
                    max_content_height = max(max_content_height, content_height)
                    x_offset += 700

                else:
                    # Other platforms use simple grouping
                    cell_id_counter, other_shapes, content_height = self._create_simple_group(
                        root, platform, platform_resources, x_offset, cell_id_counter
                    )
                    shapes.update(other_shapes)
                    max_content_height = max(max_content_height, content_height)
                    x_offset += 700

        else:
            # Flat layout without hierarchical grouping
            cell_id_counter, shapes = self._create_flat_layout(root, resources, cell_id_counter)
            max_content_height = 500  # Default height for flat layout

        return shapes, max_content_height

    def _create_azure_hierarchy(
        self, root: ET.Element, resources: list[Any], x_offset: int, cell_id: int
    ) -> tuple[int, dict[str, str], int]:
        """
        Create hierarchical Azure structure: Hub → Subnets → Resources.

        Args:
            root: mxGraph root element
            resources: Azure resources to organize
            x_offset: Starting X position
            cell_id: Starting cell ID

        Returns:
            Tuple of (next_cell_id, shape_id_map, max_content_height)
        """
        shapes = {}

        # Group Azure resources by VNet
        vnets = self._group_by_vnet(resources)

        y_offset = 50
        for vnet_name, vnet_data in vnets.items():
            # Create VNet container
            vnet_id = str(cell_id)
            cell_id += 1

            vnet_width = 850
            vnet_height = 600 if len(vnet_data["subnets"]) > 2 else 400

            # VNet container (swimlane) - using dashed border style
            vnet_label = f"{vnet_name}\\n{vnet_data.get('address_space', '')}"

            ET.SubElement(
                root,
                "mxCell",
                id=vnet_id,
                value=vnet_label,
                style="swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=50;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;fillColor=none;strokeColor=#0078D4;strokeWidth=2;fontSize=14;fontColor=#000000;dashed=1;dashPattern=5 5;",
                vertex="1",
                parent="1",
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                x=str(x_offset),
                y=str(y_offset),
                width=str(vnet_width),
                height=str(vnet_height),
                attrib={"as": "geometry"},
            )

            shapes[vnet_data.get("id", vnet_name)] = vnet_id

            # Create subnets within VNet
            subnet_y = 60
            for subnet_name, subnet_data in vnet_data["subnets"].items():
                subnet_id = str(cell_id)
                cell_id += 1

                # Determine subnet type for styling
                subnet_style = self._get_subnet_style(subnet_name)

                # Enhanced subnet label with CIDR notation (Microsoft Learn style)
                cidr = subnet_data.get("address_prefix", "")
                subnet_label = f"{subnet_name}"
                if cidr:
                    subnet_label += f"\\n{cidr}"

                ET.SubElement(
                    root,
                    "mxCell",
                    id=subnet_id,
                    value=subnet_label,
                    style=subnet_style,
                    vertex="1",
                    parent=vnet_id,
                )

                ET.SubElement(
                    root[-1],
                    "mxGeometry",
                    x="20",
                    y=str(subnet_y),
                    width=str(vnet_width - 40),
                    height="150",
                    attrib={"as": "geometry"},
                )

                shapes[subnet_data.get("id", subnet_name)] = subnet_id

                # Filter and add architectural resources within subnet (skip NICs, PIPs, disks, identities)
                resource_x = 20
                resource_y = 35  # Lower starting position for better spacing
                architectural_resources = []

                for resource in subnet_data.get("resources", []):
                    resource_label = self._format_resource_detail(resource)

                    # Skip resources that return empty labels (filtered out by _get_resource_role_label)
                    if not resource_label or resource_label.strip() == "":
                        continue

                    # Skip network infrastructure resources that clutter the diagram
                    resource_type = resource.get("type", "").lower()
                    if any(
                        skip in resource_type
                        for skip in ["networkinterface", "publicipaddress", "disk", "identity"]
                    ):
                        continue

                    architectural_resources.append(resource)

                # Place architectural resources with better spacing
                for resource in architectural_resources:
                    resource_id = str(cell_id)
                    cell_id += 1

                    resource_label = self._format_resource_detail(resource)
                    resource_style = self._get_azure_resource_style(resource)

                    ET.SubElement(
                        root,
                        "mxCell",
                        id=resource_id,
                        value=resource_label,
                        style=resource_style,
                        vertex="1",
                        parent=subnet_id,
                    )

                    # Use larger icon size for better visibility (Microsoft Learn style)
                    ET.SubElement(
                        root[-1],
                        "mxGeometry",
                        x=str(resource_x),
                        y=str(resource_y),
                        width="100",  # Wider for better icon display
                        height="90",  # Taller for better label space
                        attrib={"as": "geometry"},
                    )

                    shapes[resource.get("id", resource.get("name", ""))] = resource_id
                    resource_x += 120  # More spacing between resources

                subnet_y += 170

            y_offset += vnet_height + 50

        return cell_id, shapes, y_offset

    def _create_f5xc_group(
        self, root: ET.Element, resources: list[Any], x_offset: int, cell_id: int
    ) -> tuple[int, dict[str, str], int]:
        """
        Create F5 XC resource group.

        Returns:
            Tuple of (next_cell_id, shape_id_map, max_content_height)
        """
        shapes = {}

        group_id = str(cell_id)
        cell_id += 1

        group_width = 650
        group_height = 400

        # F5 XC container
        ET.SubElement(
            root,
            "mxCell",
            id=group_id,
            value="F5 Distributed Cloud",
            style="swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=40;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;fillColor=#50C878;strokeColor=#2E7D54;strokeWidth=2;fontSize=14;fontColor=#000000;",
            vertex="1",
            parent="1",
        )

        ET.SubElement(
            root[-1],
            "mxGeometry",
            x=str(x_offset),
            y="50",
            width=str(group_width),
            height=str(group_height),
            attrib={"as": "geometry"},
        )

        # Add F5 XC resources
        resource_x = 20
        resource_y = 60
        for resource in resources:
            resource_id = str(cell_id)
            cell_id += 1

            resource_label = f"{resource.get('type', '')}\\n{resource.get('name', '')}"
            resource_style = self.AZURE_SHAPE_STYLES["f5xc_site"]

            ET.SubElement(
                root,
                "mxCell",
                id=resource_id,
                value=resource_label,
                style=resource_style,
                vertex="1",
                parent=group_id,
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                x=str(resource_x),
                y=str(resource_y),
                width="180",
                height="100",
                attrib={"as": "geometry"},
            )

            shapes[resource.get("id", resource.get("name", ""))] = resource_id
            resource_y += 120

        # Content height is y position (50) + group height
        content_height = 50 + group_height
        return cell_id, shapes, content_height

    def _create_simple_group(
        self,
        root: ET.Element,
        platform: str,
        resources: list[Any],
        x_offset: int,
        cell_id: int,
    ) -> tuple[int, dict[str, str], int]:
        """
        Create simple resource group for other platforms.

        Returns:
            Tuple of (next_cell_id, shape_id_map, max_content_height)
        """
        shapes = {}

        group_id = str(cell_id)
        cell_id += 1

        group_width = 600
        group_height = 400

        ET.SubElement(
            root,
            "mxCell",
            id=group_id,
            value=platform,
            style=f"swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=26;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;fillColor={self.SOURCE_COLORS.get(platform, '#FFFFFF')};strokeColor=#000000;fontSize=14;fontColor=#000000;",
            vertex="1",
            parent="1",
        )

        ET.SubElement(
            root[-1],
            "mxGeometry",
            x=str(x_offset),
            y="50",
            width=str(group_width),
            height=str(group_height),
            attrib={"as": "geometry"},
        )

        # Add resources
        resource_x = 20
        resource_y = 40
        for resource in resources:
            resource_id = str(cell_id)
            cell_id += 1

            resource_label = format_resource_label(
                source=resource.get("source", ""),
                resource_type=resource.get("type", ""),
                name=resource.get("name", ""),
            )
            resource_style = self._get_resource_style(resource)

            ET.SubElement(
                root,
                "mxCell",
                id=resource_id,
                value=resource_label,
                style=resource_style,
                vertex="1",
                parent=group_id,
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                x=str(resource_x),
                y=str(resource_y),
                width="160",
                height="80",
                attrib={"as": "geometry"},
            )

            shapes[resource.get("id", resource.get("name", ""))] = resource_id
            resource_y += 100

        # Content height is y position (50) + group height
        content_height = 50 + group_height
        return cell_id, shapes, content_height

    def _create_flat_layout(
        self, root: ET.Element, resources: list[Any], cell_id: int
    ) -> tuple[int, dict[str, str]]:
        """Create flat layout without grouping."""
        shapes = {}
        x = 50
        y = 50

        for resource in resources:
            resource_id = str(cell_id)
            cell_id += 1

            resource_label = format_resource_label(
                source=resource.get("source", ""),
                resource_type=resource.get("type", ""),
                name=resource.get("name", ""),
            )
            resource_style = self._get_resource_style(resource)

            ET.SubElement(
                root,
                "mxCell",
                id=resource_id,
                value=resource_label,
                style=resource_style,
                vertex="1",
                parent="1",
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                x=str(x),
                y=str(y),
                width="160",
                height="80",
                attrib={"as": "geometry"},
            )

            shapes[resource.get("id", resource.get("name", ""))] = resource_id

            y += 100
            if y > 800:
                y = 50
                x += 200

        return cell_id, shapes

    def _generate_connections(
        self,
        root: ET.Element,
        relationships: list[Any],
        shapes: dict[str, str],
    ) -> None:
        """
        Generate mxGraph connections for relationships.

        Uses Microsoft Learn-style traffic flow arrows for different connection types.
        """
        cell_id = len(root) + 1

        for relationship in relationships:
            source_id = shapes.get(relationship.source_id)
            target_id = shapes.get(relationship.target_id)

            if not source_id or not target_id:
                logger.warning(
                    "Skipping relationship - shape not found",
                    source=relationship.source_id,
                    target=relationship.target_id,
                )
                continue

            # Determine traffic flow style based on relationship type
            relationship_type = str(relationship.relationship_type).lower()

            if "peering" in relationship_type or "vnet_peering" in relationship_type:
                style = self.TRAFFIC_FLOW_STYLES["peering"]
                label = "VNet Peering"
            elif "gateway" in relationship_type:
                style = self.TRAFFIC_FLOW_STYLES["gateway_connection"]
                label = relationship.metadata.get("label", "Gateway")
            elif "f5xc" in relationship_type or "nva" in relationship_type:
                style = self.TRAFFIC_FLOW_STYLES["nva_traffic"]
                label = relationship.metadata.get("label", "Through NVA")
            elif "internet" in relationship_type or "public" in relationship_type:
                style = self.TRAFFIC_FLOW_STYLES["north_south"]
                label = relationship.metadata.get("label", "Internet Traffic")
            elif "internal" in relationship_type or "east_west" in relationship_type:
                style = self.TRAFFIC_FLOW_STYLES["east_west"]
                label = relationship.metadata.get("label", "Internal Traffic")
            else:
                style = self.TRAFFIC_FLOW_STYLES["dependency"]
                label = relationship.metadata.get("label", str(relationship.relationship_type))

            ET.SubElement(
                root,
                "mxCell",
                id=str(cell_id),
                value=label,
                style=style,
                edge="1",
                parent="1",
                source=source_id,
                target=target_id,
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                relative="1",
                attrib={"as": "geometry"},
            )

            cell_id += 1

    def _get_resource_style(self, resource: Any) -> str:
        """Get draw.io style for resource type (backward compatibility)."""
        resource_type = get_resource_short_name(resource.get("type", "")).lower()

        # Use new Azure shape styles if Azure resource
        if resource.get("source") in [ResourceSource.AZURE, "azure"]:
            return self._get_azure_resource_style(resource)

        # Fallback to simple styles for non-Azure
        if "site" in resource_type:
            return self.AZURE_SHAPE_STYLES["f5xc_site"]
        else:
            return self.AZURE_SHAPE_STYLES["default"]

    def _get_azure_resource_style(self, resource: Any) -> str:
        """Get Azure-specific resource style with proper Azure shapes."""
        resource_type = get_resource_short_name(resource.get("type", "")).lower()

        # Map resource types to Azure shapes
        if "virtualmachine" in resource_type or "vm" in resource_type:
            return self.AZURE_SHAPE_STYLES["vm"]
        elif "loadbalancer" in resource_type or "_lb" in resource_type:
            return self.AZURE_SHAPE_STYLES["lb"]
        elif "gateway" in resource_type:
            return self.AZURE_SHAPE_STYLES["gateway"]
        elif "networksecuritygroup" in resource_type or "nsg" in resource_type:
            return self.AZURE_SHAPE_STYLES["nsg"]
        elif "networkinterface" in resource_type or "nic" in resource_type:
            return self.AZURE_SHAPE_STYLES["nic"]
        elif "publicipaddress" in resource_type or "pip" in resource_type:
            return self.AZURE_SHAPE_STYLES["pip"]
        elif "routetable" in resource_type:
            return self.AZURE_SHAPE_STYLES["route_table"]
        else:
            return self.AZURE_SHAPE_STYLES["default"]

    def _get_subnet_style(self, subnet_name: str) -> str:
        """Determine subnet style based on name and purpose."""
        subnet_lower = subnet_name.lower()

        if "gateway" in subnet_lower or subnet_lower == "gatewaysubnet":
            return self.AZURE_SHAPE_STYLES["gateway_subnet"]
        elif "nva" in subnet_lower or "firewall" in subnet_lower or "appliance" in subnet_lower:
            return self.AZURE_SHAPE_STYLES["nva_subnet"]
        else:
            return self.AZURE_SHAPE_STYLES["subnet"]

    def _get_resource_role_label(self, resource: Any) -> str:
        """
        Get clean, role-based resource label matching Microsoft Learn standards.

        Maps Azure resources to architectural roles rather than technical names.
        Examples: "NVA", "App server", "Gateway", "Load balancer"

        Priority: Resource TYPE checks (definitive) before NAME pattern checks (heuristic)
        """
        name = resource.get("name", "").lower()
        resource_type = resource.get("type", "").lower()

        # === PHASE 1: Resource TYPE checks (most reliable) ===

        # Load Balancers (check before NVA name patterns)
        if "loadbalancer" in resource_type or "lb" in resource_type:
            if "internal" in name or "private" in name:
                return "Internal LB"
            elif "public" in name or "external" in name:
                return "Public LB"
            return "Load balancer"

        # Gateways
        if "gateway" in resource_type:
            if "vpn" in name:
                return "VPN GW"
            elif "expressroute" in name or "er" in name:
                return "ExpressRoute GW"
            return "Gateway"

        # Network Security Groups
        if "networksecuritygroup" in resource_type or "nsg" in resource_type:
            if "mgmt" in name or "management" in name:
                return "Mgmt NSG"
            elif "workload" in name or "app" in name:
                return "Workload NSG"
            elif "nva" in name or "firewall" in name:
                return "NVA NSG"
            elif "gateway" in name:
                return "Gateway NSG"
            return "NSG"

        # Route Tables
        if "routetable" in resource_type or "route_table" in resource_type:
            if "hub" in name:
                return "Hub routes"
            elif "spoke" in name:
                return "Spoke routes"
            return "Route table"

        # Virtual Machines (check type first, then refine by name)
        if "virtualmachine" in resource_type or "vm" in resource_type:
            # Check for F5 XC CE VMs specifically (NVA role)
            if ("f5" in name and "xc" in name) or ("ce" in name and "vm" in name):
                if "01" in name or "-1" in name:
                    return "NVA-1"
                elif "02" in name or "-2" in name:
                    return "NVA-2"
                return "NVA"
            # General VM role detection
            elif "app" in name or "web" in name:
                return "App server"
            elif "db" in name or "sql" in name or "database" in name:
                return "Database"
            elif "jump" in name or "bastion" in name:
                return "Jumpbox"
            return "VM"

        # Storage
        if "storage" in resource_type:
            return "Storage"

        # === PHASE 2: Infrastructure filtering (always filter these) ===

        if any(
            skip in resource_type
            for skip in [
                "networkinterface",
                "publicipaddress",
                "subnet_network_security_group_association",
                "subnet_route_table_association",
                "virtual_network_peering",
            ]
        ):
            return None  # Skip these - they clutter the diagram

        # === PHASE 3: Fallback - use short type name ===

        return get_resource_short_name(resource_type)

    def _format_resource_detail(self, resource: Any) -> str:
        """
        Format resource label for Microsoft Learn style diagrams.

        Returns clean, role-based labels with optional key details like IP addresses.
        """
        # Get role-based label
        role_label = self._get_resource_role_label(resource)

        # Skip resources that shouldn't appear in architecture diagrams
        if role_label is None:
            return ""

        # Extract key details
        values = resource.get("values", {})
        properties = resource.get("properties", {})

        # Only add IP for load balancers and key network resources
        resource_type = resource.get("type", "").lower()
        label_parts = [role_label]

        if "loadbalancer" in resource_type:
            # Show IP for load balancers
            if "private_ip_address" in values:
                label_parts.append(values["private_ip_address"])
            elif properties.get("frontendIPConfigurations"):
                # Extract from Azure properties structure
                frontend_ips = properties.get("frontendIPConfigurations", [])
                if frontend_ips and isinstance(frontend_ips, list):
                    ip = frontend_ips[0].get("properties", {}).get("privateIPAddress")
                    if ip:
                        label_parts.append(ip)

        return "\\n".join(label_parts)

    def _group_by_vnet(self, resources: list[Any]) -> dict[str, Any]:
        """
        Group Azure resources hierarchically by VNet and Subnet.

        Returns:
            Dict mapping VNet names to their subnets and resources:
            {
                "hub-vnet": {
                    "id": "vnet_id",
                    "address_space": "10.0.0.0/16",
                    "subnets": {
                        "GatewaySubnet": {
                            "id": "subnet_id",
                            "address_prefix": "10.0.1.0/24",
                            "resources": [list of VMs, NICs, etc.]
                        },
                        ...
                    }
                },
                ...
            }
        """
        vnets = {}

        # First pass: identify VNets and subnets
        for resource in resources:
            resource_type = resource.get("type", "").lower()

            if "virtualnetwork" in resource_type and "subnet" not in resource_type:
                # This is a VNet
                vnet_name = resource.get("name", "unnamed-vnet")
                values = resource.get("values", {})

                vnets[vnet_name] = {
                    "id": resource.get("id", vnet_name),
                    "address_space": (
                        values.get("address_space", [""])[0]
                        if isinstance(values.get("address_space"), list)
                        else values.get("address_space", "")
                    ),
                    "subnets": {},
                }

            elif "subnet" in resource_type:
                # This is a subnet
                subnet_name = resource.get("name", "unnamed-subnet")
                values = resource.get("values", {})

                # Try to find parent VNet
                vnet_name = values.get("virtual_network_name", "default-vnet")

                if vnet_name not in vnets:
                    vnets[vnet_name] = {
                        "id": vnet_name,
                        "address_space": "",
                        "subnets": {},
                    }

                vnets[vnet_name]["subnets"][subnet_name] = {
                    "id": resource.get("id", subnet_name),
                    "address_prefix": values.get("address_prefix", ""),
                    "resources": [],
                }

        # Second pass: assign resources to subnets
        for resource in resources:
            resource_type = resource.get("type", "").lower()

            # Skip VNets and subnets themselves
            if "virtualnetwork" in resource_type or "subnet" in resource_type:
                continue

            # Try to find which subnet this resource belongs to
            values = resource.get("values", {})
            properties = resource.get("properties", {})

            # Extract subnet_id based on resource type
            subnet_id = values.get("subnet_id") or properties.get("subnet", {}).get("id", "")

            # Special handling for load balancers - subnet is in frontend IP configuration
            if not subnet_id and ("loadbalancer" in resource_type or "lb" in resource_type):
                frontend_configs = values.get("frontend_ip_configuration", [])
                if frontend_configs and isinstance(frontend_configs, list):
                    subnet_id = frontend_configs[0].get("subnet_id", "")

            # Try to match to a subnet
            assigned = False
            for _vnet_name, vnet_data in vnets.items():
                for _subnet_name, subnet_data in vnet_data["subnets"].items():
                    if subnet_id and subnet_data["id"] in subnet_id:
                        subnet_data["resources"].append(resource)
                        assigned = True
                        break
                if assigned:
                    break

            # If not assigned to any subnet, create a default subnet
            if not assigned and vnets:
                default_vnet = list(vnets.keys())[0]
                if "default-subnet" not in vnets[default_vnet]["subnets"]:
                    vnets[default_vnet]["subnets"]["default-subnet"] = {
                        "id": "default-subnet",
                        "address_prefix": "",
                        "resources": [],
                    }
                vnets[default_vnet]["subnets"]["default-subnet"]["resources"].append(resource)

        return vnets

    def _group_resources_by_platform(self, resources: list[Any]) -> dict[str, list[Any]]:
        """Group resources by source platform."""
        grouped: dict[str, list[Any]] = {
            "Terraform": [],
            "Azure": [],
            "F5 XC": [],
        }

        for resource in resources:
            source = resource.get("source", "")
            if source == ResourceSource.TERRAFORM or source == "terraform":
                grouped["Terraform"].append(resource)
            elif source == ResourceSource.AZURE or source == "azure":
                grouped["Azure"].append(resource)
            elif source == ResourceSource.F5XC or source == "f5xc":
                grouped["F5 XC"].append(resource)

        # Remove empty groups
        return {k: v for k, v in grouped.items() if v}

    def _add_internet_cloud(self, root: ET.Element, cell_id: int) -> int:
        """
        Add Internet cloud shape at the top of the diagram.
        Matches Microsoft Learn style with prominent cloud icon.

        Returns:
            Next available cell ID
        """
        cloud_id = str(cell_id)
        cell_id += 1

        ET.SubElement(
            root,
            "mxCell",
            id=cloud_id,
            value="Internet",
            style=self.AZURE_SHAPE_STYLES["internet_cloud"],
            vertex="1",
            parent="1",
        )

        ET.SubElement(
            root[-1],
            "mxGeometry",
            x="700",
            y="10",
            width="200",
            height="100",
            attrib={"as": "geometry"},
        )

        logger.debug("Added Internet cloud element", cell_id=cloud_id)
        return cell_id

    def _add_sequence_indicators(
        self, root: ET.Element, cell_id: int, positions: list[tuple[int, int, str]]
    ) -> int:
        """
        Add numbered sequence indicators (green circles with numbers).
        Matches Microsoft Learn traffic flow sequence style.

        Args:
            root: mxGraph root element
            cell_id: Starting cell ID
            positions: List of (x, y, number) tuples for each indicator

        Returns:
            Next available cell ID
        """
        for x, y, number in positions:
            indicator_id = str(cell_id)
            cell_id += 1

            ET.SubElement(
                root,
                "mxCell",
                id=indicator_id,
                value=number,
                style=self.AZURE_SHAPE_STYLES["sequence_number"],
                vertex="1",
                parent="1",
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                x=str(x),
                y=str(y),
                width="30",
                height="30",
                attrib={"as": "geometry"},
            )

        logger.debug(f"Added {len(positions)} sequence indicators")
        return cell_id

    def _add_traffic_legend(self, root: ET.Element, cell_id: int, y_position: int = 100) -> int:
        """
        Add traffic flow legend showing inbound (blue) and return (green) traffic.
        Matches Microsoft Learn diagram legend style.

        Args:
            root: mxGraph root element
            cell_id: Starting cell ID
            y_position: Y position for legend (should be below all content)

        Returns:
            Next available cell ID
        """
        # Text labels for legend (not using lines as they don't show labels well)
        inbound_label_id = str(cell_id)
        cell_id += 1

        ET.SubElement(
            root,
            "mxCell",
            id=inbound_label_id,
            value="━━━━ Inbound traffic",
            style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=12;fontColor=#4472C4;fontStyle=1;",
            vertex="1",
            parent="1",
        )

        ET.SubElement(
            root[-1],
            "mxGeometry",
            x="50",
            y=str(y_position),
            width="200",
            height="30",
            attrib={"as": "geometry"},
        )

        # Return traffic label
        return_label_id = str(cell_id)
        cell_id += 1

        ET.SubElement(
            root,
            "mxCell",
            id=return_label_id,
            value="━━━━ Return traffic",
            style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=12;fontColor=#70AD47;fontStyle=1;",
            vertex="1",
            parent="1",
        )

        ET.SubElement(
            root[-1],
            "mxGeometry",
            x="50",
            y=str(y_position + 35),
            width="200",
            height="30",
            attrib={"as": "geometry"},
        )

        logger.debug(f"Added traffic flow legend at y={y_position}")
        return cell_id

    def _add_azure_branding(
        self, root: ET.Element, cell_id: int, y_position: Optional[int] = None
    ) -> int:
        """
        Add Microsoft Azure branding footer.
        Matches Microsoft Learn diagram branding style.

        Args:
            root: mxGraph root element
            cell_id: Current cell ID
            y_position: Optional Y position for branding. If None, uses default page height.

        Returns:
            Next available cell ID
        """
        branding_id = str(cell_id)
        cell_id += 1

        # Use provided y_position or default to bottom of page
        y_pos = y_position if y_position is not None else self.layout["page_height"] - 40

        # Microsoft Azure logo text
        ET.SubElement(
            root,
            "mxCell",
            id=branding_id,
            value="Microsoft Azure",
            style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=11;fontColor=#0078D4;fontStyle=1;",
            vertex="1",
            parent="1",
        )

        ET.SubElement(
            root[-1],
            "mxGeometry",
            x=str(self.layout["page_width"] - 200),
            y=str(y_pos),
            width="150",
            height="30",
            attrib={"as": "geometry"},
        )

        logger.debug("Added Azure branding", y_position=y_pos)
        return cell_id

    def _save_diagram(self, diagram_xml: ET.Element) -> Path:
        """Save diagram XML to file."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in self.title)
        output_file = self.output_dir / f"{safe_title}.drawio"

        # Pretty print XML
        xml_string = ET.tostring(diagram_xml, encoding="unicode")
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

        logger.info("Diagram saved to file", path=str(output_file))
        return output_file

    def _export_to_png(self, drawio_file: Path) -> Path:
        """
        Export .drawio file to PNG using drawio CLI.

        Args:
            drawio_file: Path to the .drawio file to export

        Returns:
            Path to the exported PNG file

        Raises:
            DiagramGenerationError: If PNG export fails
        """
        png_file = drawio_file.with_suffix(".png")

        try:
            # Use drawio CLI to export PNG
            # --export: export mode
            # --format png: output format
            # --transparent: transparent background
            # --border 10: add border around diagram
            # --crop: crop to diagram size
            subprocess.run(
                [
                    "drawio",
                    "--export",
                    "--format",
                    "png",
                    "--transparent",
                    "--border",
                    "10",
                    "--crop",
                    "--output",
                    str(png_file),
                    str(drawio_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("PNG export successful", png_file=str(png_file))
            return png_file

        except subprocess.CalledProcessError as e:
            error_msg = f"PNG export failed: {e.stderr}"
            logger.error(error_msg, returncode=e.returncode)
            raise DiagramGenerationError(error_msg) from e
        except FileNotFoundError:
            error_msg = "drawio CLI not found. Install with: brew install --cask drawio"
            logger.error(error_msg)
            raise DiagramGenerationError(error_msg) from None

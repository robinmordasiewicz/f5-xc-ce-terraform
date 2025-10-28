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

from diagram_generator.azure_icons import get_azure_icon_converter
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

    # Azure resource shapes using geometric shapes (Microsoft Learn style)
    AZURE_SHAPE_STYLES = {
        # VNet containers - dashed border like Microsoft Learn
        "vnet": "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#0078D4;strokeWidth=2;fontSize=12;fontStyle=1;dashed=1;dashPattern=5 5;",
        "subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=10;verticalAlign=top;",
        "gateway_subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=10;verticalAlign=top;",
        "nva_subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=10;verticalAlign=top;",
        # Azure resource icons using simple geometric shapes
        "vm": "rounded=1;whiteSpace=wrap;html=1;fillColor=#00A4EF;strokeColor=#0078D4;strokeWidth=2;fontSize=10;fontColor=#FFFFFF;fontStyle=1;",  # Rounded rectangle for VMs
        "lb": "shape=rhombus;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;fillColor=#00BCF2;strokeColor=#0078D4;strokeWidth=2;fontSize=10;fontColor=#000000;fontStyle=1;",  # Diamond for load balancers
        "gateway": "shape=rhombus;perimeter=rhombusPerimeter;whiteSpace=wrap;html=1;fillColor=#FF6C37;strokeColor=#CC5529;strokeWidth=2;fontSize=10;fontColor=#FFFFFF;fontStyle=1;",  # Diamond for gateways
        "nsg": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFF4CE;strokeColor=#FF8C00;strokeWidth=2;fontSize=9;fontColor=#000000;",  # Rectangle for NSGs
        "nic": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F4F8;strokeColor=#0078D4;strokeWidth=1;fontSize=9;",
        "pip": "ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#00BCF2;strokeColor=#0078D4;strokeWidth=2;fontSize=9;fontColor=#FFFFFF;",
        # Special elements matching Microsoft Learn
        "internet_cloud": "ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#5D9CEC;strokeColor=#FFFFFF;strokeWidth=2;fontColor=#FFFFFF;fontSize=14;fontStyle=1;",
        "onpremises_building": "rounded=0;whiteSpace=wrap;html=1;fillColor=#0078D4;strokeColor=#005A9E;strokeWidth=2;fontSize=10;fontColor=#FFFFFF;",  # Simple building rectangle
        "route_table": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;strokeWidth=1;fontSize=9;align=left;verticalAlign=top;",
        "sequence_number": "ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#107C10;strokeColor=#FFFFFF;strokeWidth=3;fontColor=#FFFFFF;fontSize=14;fontStyle=1;shadow=1;",
        "f5xc_site": "shape=cloud;fillColor=#50C878;strokeColor=#2E7D54;strokeWidth=2;",
        "default": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F4F8;strokeColor=#0078D4;strokeWidth=1;",
    }

    # Traffic flow arrow styles (matching Microsoft Learn)
    # Using official Azure brand colors: #0078D4 (Azure Blue), #107C10 (Success Green)
    # Thick 6px arrows for high visibility matching Microsoft Learn diagrams
    TRAFFIC_FLOW_STYLES = {
        "inbound": "endArrow=classic;html=1;strokeColor=#0078D4;strokeWidth=6;",  # Inbound traffic (Azure blue)
        "return": "endArrow=classic;html=1;strokeColor=#107C10;strokeWidth=6;",  # Return traffic (success green)
        "north_south": "endArrow=classic;html=1;strokeColor=#0078D4;strokeWidth=6;",  # Internet traffic (Azure blue)
        "east_west": "endArrow=classic;html=1;strokeColor=#107C10;strokeWidth=6;",  # Internal traffic (success green)
        "peering": "endArrow=classic;html=1;strokeColor=#666666;strokeWidth=4;dashed=1;",  # VNet peering (thicker)
        "gateway_connection": "endArrow=classic;html=1;strokeColor=#0078D4;strokeWidth=6;",  # Gateway traffic (Azure blue)
        "nva_traffic": "endArrow=classic;html=1;strokeColor=#107C10;strokeWidth=6;",  # Through NVA (success green)
        "dependency": "endArrow=classic;html=1;strokeColor=#666666;strokeWidth=4;dashed=1;",  # Generic dependency (thicker)
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

        # Initialize Azure icon converter
        self.icon_converter = get_azure_icon_converter()

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

    def generate(
        self,
        correlated_resources: CorrelatedResources,
        lb_relationships: dict[str, Any] | None = None,
        route_relationships: dict[str, Any] | None = None,
    ) -> DrawioDocument:
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
            diagram_xml = self._create_diagram_xml(
                correlated_resources,
                lb_relationships=lb_relationships or {},
                route_relationships=route_relationships or {},
            )

            # Save to file
            output_file = self._save_diagram(diagram_xml)

            # Export to SVG (properly renders embedded base64 SVG icons)
            svg_file = self._export_to_svg(output_file)

            logger.info(
                "Draw.io diagram generated successfully",
                file_path=str(output_file),
                image_file_path=str(svg_file),
            )

            return DrawioDocument(
                file_path=output_file,
                image_file_path=svg_file,
                title=self.title,
            )

        except Exception as e:
            logger.error("Draw.io diagram generation failed", error=str(e))
            raise DiagramGenerationError(f"Failed to generate draw.io diagram: {e}") from e

    def _create_diagram_xml(
        self,
        correlated_resources: CorrelatedResources,
        lb_relationships: dict[str, Any] | None = None,
        route_relationships: dict[str, Any] | None = None,
    ) -> ET.Element:
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

        # Detect traffic flows from Azure topology
        traffic_flows = []
        if lb_relationships or route_relationships:
            traffic_flows = self._detect_traffic_flows(
                lb_relationships=lb_relationships or {},
                route_relationships=route_relationships or {},
                resources=correlated_resources.resources,
                shapes=shapes,
            )
            logger.info(f"Detected {len(traffic_flows)} traffic flow paths")

        # Generate connections (both from correlator and detected traffic flows)
        all_relationships = list(correlated_resources.relationships)

        # Convert traffic flows to relationship format for rendering
        for source_id, target_id, flow_type, metadata in traffic_flows:
            # Create a pseudo-relationship for the traffic flow
            flow_relationship = type(
                "obj",
                (object,),
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship_type": flow_type,
                    "metadata": metadata,
                },
            )()
            all_relationships.append(flow_relationship)

        self._generate_connections(root, all_relationships, shapes)

        # Add Microsoft Learn styling elements
        cell_id = len(root) + 1

        # Add Internet cloud at the top (centered above hub VNet)
        # Use hub VNet position from layout tracking or fallback to default
        hub_x = self.layout.get("hub_vnet_x", 700)
        hub_width = self.layout.get("hub_vnet_width", 850)
        cell_id = self._add_internet_cloud(
            root, cell_id, hub_vnet_x=hub_x, hub_vnet_width=hub_width
        )

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

                elif platform == "Terraform":
                    # Skip Terraform resources - they clutter Microsoft Learn style diagrams
                    logger.info(
                        f"Skipping {len(platform_resources)} Terraform resources for cleaner diagram"
                    )
                    continue

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

        Implements Microsoft Learn architectural layout standards:
        - Hub VNets positioned at top (y=150)
        - Spoke VNets positioned below hub (y=850+)
        - Internet cloud centered above hub VNet

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

        # Sort VNets: Hub first, then spokes (alphabetically within each group)
        # This follows Microsoft Learn architectural diagram conventions
        sorted_vnets = sorted(
            vnets.items(),
            key=lambda x: (
                0 if self._classify_vnet_role(x[0], x[1]) == "hub" else 1,
                x[0],  # Alphabetical within each group
            ),
        )

        # Track hub VNet position for Internet cloud centering
        hub_vnet_x = None

        # Vertical layout: Hub at top (y=150), spokes below with consistent spacing
        hub_y_position = 150  # Below Internet cloud (bottom at y=110), gap = 40px
        vnet_height = 400  # Standard VNet container height
        vnet_spacing = 50  # Slightly larger spacing to match Internet-to-Hub visual gap
        spoke_y_position = hub_y_position + vnet_height + vnet_spacing  # 150 + 400 + 50 = 600
        vnet_vertical_spacing = (
            vnet_height + vnet_spacing
        )  # Space between stacked spoke VNets (540px)

        current_spoke_y = spoke_y_position

        for vnet_name, vnet_data in sorted_vnets:
            # Create VNet container
            vnet_id = str(cell_id)
            cell_id += 1

            vnet_width = 850
            vnet_height = 600 if len(vnet_data["subnets"]) > 2 else 400

            # Determine VNet role and position
            vnet_role = self._classify_vnet_role(vnet_name, vnet_data)

            # Position based on role: hub at top, spokes stacked vertically below
            if vnet_role == "hub":
                vnet_y = hub_y_position
                # Track first hub VNet position for Internet cloud centering
                if hub_vnet_x is None:
                    hub_vnet_x = x_offset
                    # Store hub position for later Internet cloud update
                    self.layout["hub_vnet_x"] = x_offset
                    self.layout["hub_vnet_width"] = vnet_width
            else:
                # Spoke VNets stack vertically below hub
                vnet_y = current_spoke_y
                current_spoke_y += vnet_vertical_spacing

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
                y=str(vnet_y),
                width=str(vnet_width),
                height=str(vnet_height),
                attrib={"as": "geometry"},
            )

            shapes[vnet_data.get("id", vnet_name)] = vnet_id

            # Create subnets within VNet (skip empty subnets for cleaner diagrams)
            subnet_y = 60
            for subnet_name, subnet_data in vnet_data["subnets"].items():
                # Pre-filter architectural resources to check if subnet has any meaningful content
                temp_architectural_resources = []
                for resource in subnet_data.get("resources", []):
                    resource_label = self._format_resource_detail(resource)
                    # Skip resources that return empty labels
                    if not resource_label or resource_label.strip() == "":
                        continue
                    # Skip network infrastructure resources that clutter the diagram
                    resource_type = resource.get("type", "").lower()
                    if any(
                        skip in resource_type
                        for skip in ["networkinterface", "publicipaddress", "disk", "identity"]
                    ):
                        continue
                    temp_architectural_resources.append(resource)

                # Skip empty subnets (Microsoft Learn diagrams omit empty containers)
                if not temp_architectural_resources:
                    logger.debug(f"Skipping empty subnet: {subnet_name}")
                    continue

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

                # Use pre-filtered architectural resources
                resource_x = 20
                resource_y = 35  # Lower starting position for better spacing
                architectural_resources = temp_architectural_resources

                # Note: architectural_resources was already filtered in lines 400-412
                # This loop should NOT append to the list - just process existing items

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

        # Return max Y coordinate for positioning legend and branding
        max_y = current_spoke_y if current_spoke_y > hub_y_position + 600 else hub_y_position + 600
        return cell_id, shapes, max_y

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

    def _detect_traffic_flows(
        self,
        lb_relationships: dict[str, Any],
        route_relationships: dict[str, Any],
        resources: list[Any],
        shapes: dict[str, str],
    ) -> list[tuple[str, str, str, dict[str, Any]]]:
        """
        Detect traffic flow paths from Azure topology data.

        Analyzes load balancer backend pools, route tables, and resource relationships
        to identify actual data flow paths for visualization.

        Args:
            lb_relationships: Load balancer backend pool and frontend configs
            route_relationships: Route table next-hop configurations
            resources: All collected Azure resources
            shapes: Map of resource IDs to shape IDs

        Returns:
            List of (source_id, target_id, flow_type, metadata) tuples
        """
        flows = []
        logger.info("Detecting traffic flows from Azure topology")

        # 1. Detect load balancer traffic flows
        for lb_id, lb_data in lb_relationships.items():
            lb_name = lb_data["name"]
            is_public = lb_data["is_public"]

            # Traffic type based on LB type
            flow_type = "north_south" if is_public else "east_west"

            # Create flows from LB to each backend target
            for target_id in lb_data["backend_targets"]:
                # Backend IP configs are nested in NICs - extract NIC ID
                if "/networkInterfaces/" in target_id:
                    nic_id = target_id.split("/ipConfigurations/")[0]

                    # Find the VM that owns this NIC
                    for resource in resources:
                        if resource.get("type", "").lower() == "microsoft.compute/virtualmachines":
                            vm_props = resource.get("properties", {})
                            network_profile = vm_props.get("networkProfile", {})
                            nic_refs = network_profile.get("networkInterfaces", [])

                            for nic_ref in nic_refs:
                                if isinstance(nic_ref, dict) and nic_ref.get("id") == nic_id:
                                    vm_id = resource.get("id", "")
                                    if lb_id in shapes and vm_id in shapes:
                                        flows.append(
                                            (
                                                lb_id,
                                                vm_id,
                                                flow_type,
                                                {
                                                    "label": "Backend pool traffic",
                                                    "lb_name": lb_name,
                                                    "is_public": is_public,
                                                },
                                            )
                                        )
                                    break

        # 2. Detect route table traffic flows (next-hop through NVA)
        for _rt_id, rt_data in route_relationships.items():
            rt_name = rt_data["name"]

            for next_hop in rt_data["next_hops"]:
                if next_hop["type"] == "VirtualAppliance" and next_hop["ip"]:
                    # Find NVA by next-hop IP
                    nva_ip = next_hop["ip"]

                    # Search for VM/NIC with this private IP
                    for resource in resources:
                        if (
                            resource.get("type", "").lower()
                            == "microsoft.network/networkinterfaces"
                        ):
                            nic_props = resource.get("properties", {})
                            ip_configs = nic_props.get("ipConfigurations", [])

                            for ip_config in ip_configs:
                                if isinstance(ip_config, dict):
                                    ip_props = ip_config.get("properties", {})
                                    private_ip = ip_props.get("privateIPAddress", "")

                                    if private_ip == nva_ip:
                                        # Found the NVA NIC - now find the VM
                                        nic_id = resource.get("id", "")

                                        for vm in resources:
                                            if (
                                                vm.get("type", "").lower()
                                                == "microsoft.compute/virtualmachines"
                                            ):
                                                vm_props = vm.get("properties", {})
                                                network_profile = vm_props.get("networkProfile", {})
                                                nic_refs = network_profile.get(
                                                    "networkInterfaces", []
                                                )

                                                for nic_ref in nic_refs:
                                                    if (
                                                        isinstance(nic_ref, dict)
                                                        and nic_ref.get("id") == nic_id
                                                    ):
                                                        vm_id = vm.get("id", "")

                                                        # Create flow for any subnet using this route table
                                                        for subnet_id in rt_data[
                                                            "associated_subnets"
                                                        ]:
                                                            if vm_id in shapes:
                                                                flows.append(
                                                                    (
                                                                        subnet_id,
                                                                        vm_id,
                                                                        "nva_traffic",
                                                                        {
                                                                            "label": f"Route through {nva_ip}",
                                                                            "route_table": rt_name,
                                                                            "next_hop_ip": nva_ip,
                                                                        },
                                                                    )
                                                                )

        logger.info(f"Detected {len(flows)} traffic flows")
        return flows

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

            # Create edge cell
            edge_cell = ET.SubElement(
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

            # Create geometry with explicit points for arrow visibility
            geometry = ET.SubElement(
                edge_cell,
                "mxGeometry",
                relative="1",
                attrib={"as": "geometry"},
            )

            # Add source and target points (relative to shape centers)
            # These ensure Draw.io renders the arrows correctly
            ET.SubElement(
                geometry,
                "mxPoint",
                x="0",
                y="0",
                attrib={"as": "sourcePoint"},
            )

            ET.SubElement(
                geometry,
                "mxPoint",
                x="0",
                y="0",
                attrib={"as": "targetPoint"},
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
        """Get Azure-specific resource style with proper Azure shapes and icons."""
        # Extract resource type directly from the resource (not using get_resource_short_name which returns name)
        full_resource_type = resource.get("type", "").lower()

        # Extract the short type name from full Azure resource type
        # Example: "microsoft.compute/virtualmachines" -> "virtualmachines"
        if "/" in full_resource_type:
            resource_type = full_resource_type.split("/")[-1]
        else:
            resource_type = full_resource_type

        # Icon type mapping (maps short Azure type names to icon keys)
        icon_type_map = {
            "virtualmachines": "virtual_machine",
            "vm": "vm",
            "loadbalancers": "load_balancer",
            "lb": "lb",
            "virtualnetworkgateways": "virtual_network_gateway",
            "gateway": "virtual_network_gateway",
            "networksecuritygroups": "network_security_group",
            "nsg": "nsg",
            "networkinterfaces": "network_interface",
            "nic": "nic",
            "publicipaddresses": "public_ip",
            "pip": "public_ip",
            "routetables": "route_table",
        }

        # Find matching icon type
        icon_resource_type = icon_type_map.get(resource_type)

        # Try to use Azure icon if available
        if icon_resource_type:
            icon_data = self.icon_converter.get_icon_for_resource(icon_resource_type)
            if icon_data:
                logger.debug(f"Using Azure icon for {resource_type}: {icon_data['icon_path']}")
                return icon_data["style"]

        # Fallback to geometric shapes if icon not available
        logger.debug(f"No icon available for {resource_type}, using geometric shapes")
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

    def _classify_vnet_role(self, vnet_name: str, vnet_data: dict) -> str:
        """
        Classify VNet as 'hub' or 'spoke' based on naming and resource characteristics.

        Hub VNets typically contain:
        - Gateway subnets (VPN/ExpressRoute gateways)
        - NVA subnets (Network Virtual Appliances, firewalls)
        - Shared services (DNS, Active Directory)

        Args:
            vnet_name: VNet name
            vnet_data: VNet metadata including subnets

        Returns:
            'hub' or 'spoke'
        """
        name_lower = vnet_name.lower()

        # Explicit naming convention check
        if "hub" in name_lower:
            return "hub"
        if "spoke" in name_lower:
            return "spoke"

        # Heuristic: Hub VNets contain gateway or NVA infrastructure
        subnets = vnet_data.get("subnets", {})

        # Check for gateway subnet (standard Azure naming)
        has_gateway = any("gatewaysubnet" in s.lower() for s in subnets)

        # Check for NVA/firewall subnet
        has_nva = any(
            keyword in s.lower()
            for s in subnets
            for keyword in ["nva", "firewall", "external", "dmz"]
        )

        # Check for shared services indicators
        has_shared_services = any(
            keyword in s.lower()
            for s in subnets
            for keyword in ["shared", "services", "management", "mgmt"]
        )

        # Hub VNets typically have gateway or NVA infrastructure
        if has_gateway or has_nva:
            return "hub"

        # If has shared services but no gateway/NVA, likely still a hub
        if has_shared_services and len(subnets) > 1:
            return "hub"

        # Default to spoke for application workload VNets
        return "spoke"

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

        # First pass: identify VNets and extract their subnets
        for resource in resources:
            resource_type = resource.get("type", "").lower()

            if "virtualnetwork" in resource_type and "subnet" not in resource_type:
                # This is a VNet
                vnet_name = resource.get("name", "unnamed-vnet")
                values = resource.get("values", {})
                properties = resource.get("properties", {})

                # Get address space from either values (Terraform) or properties (Azure)
                address_space = ""
                if "address_space" in values:
                    address_space = (
                        values["address_space"][0]
                        if isinstance(values["address_space"], list)
                        else values["address_space"]
                    )
                elif (
                    "addressSpace" in properties and "addressPrefixes" in properties["addressSpace"]
                ):
                    prefixes = properties["addressSpace"]["addressPrefixes"]
                    address_space = prefixes[0] if prefixes else ""

                vnets[vnet_name] = {
                    "id": resource.get("id", vnet_name),
                    "address_space": address_space,
                    "subnets": {},
                }

                # Extract subnets from VNet properties (Azure Resource Graph structure)
                subnets_list = properties.get("subnets", [])
                for subnet_data in subnets_list:
                    subnet_name = subnet_data.get("name", "unnamed-subnet")
                    subnet_properties = subnet_data.get("properties", {})

                    vnets[vnet_name]["subnets"][subnet_name] = {
                        "id": subnet_data.get("id", f"{vnet_name}/{subnet_name}"),
                        "address_prefix": subnet_properties.get("addressPrefix", ""),
                        "resources": [],
                    }

                # Also handle Terraform subnet resources (if present as separate resources)
            elif "subnet" in resource_type:
                # This is a Terraform subnet resource
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

                # Only add if not already present from VNet properties
                if subnet_name not in vnets[vnet_name]["subnets"]:
                    vnets[vnet_name]["subnets"][subnet_name] = {
                        "id": resource.get("id", subnet_name),
                        "address_prefix": values.get("address_prefix", ""),
                        "resources": [],
                    }

        # Second pass: assign resources to subnets
        logger.debug(f"Starting second pass: assigning {len(resources)} resources to subnets")
        for idx, resource in enumerate(resources, 1):
            logger.debug(f"=== LOOP ITERATION {idx}/{len(resources)} START ===")
            logger.debug(f"Resource object type: {type(resource)}")
            logger.debug(
                f"Resource keys: {list(resource.keys()) if isinstance(resource, dict) else 'NOT A DICT'}"
            )

            resource_type = resource.get("type", "").lower()
            resource_name = resource.get("name", "").lower()
            logger.debug(
                f"Processing resource {idx}/{len(resources)}: {resource_name} (type: {resource_type})"
            )

            # Skip VNets and subnets themselves
            if "virtualnetwork" in resource_type or "subnet" in resource_type:
                logger.debug(f"Skipping VNet/subnet resource: {resource_name}")
                continue

            values = resource.get("values", {})
            properties = resource.get("properties", {})

            # Extract subnet_id based on resource type
            subnet_id = values.get("subnet_id") or properties.get("subnet", {}).get("id", "")

            # Special handling for load balancers - subnet is in frontend IP configuration
            if not subnet_id and ("loadbalancer" in resource_type or "lb" in resource_type):
                logger.debug(
                    f"LB {resource_name}: Attempting to extract subnet from frontendIPConfigurations"
                )
                # Try Terraform structure first
                frontend_configs = values.get("frontend_ip_configuration", [])
                logger.debug(f"LB {resource_name}: Terraform frontend_configs={frontend_configs}")
                if frontend_configs and isinstance(frontend_configs, list):
                    subnet_id = frontend_configs[0].get("subnet_id", "")
                    logger.debug(f"LB {resource_name}: Terraform subnet_id={subnet_id}")

                # Try Azure Resource Graph structure
                if not subnet_id:
                    frontend_configs = properties.get("frontendIPConfigurations", [])
                    logger.debug(
                        f"LB {resource_name}: Azure Resource Graph frontend_configs={frontend_configs}"
                    )
                    if frontend_configs and isinstance(frontend_configs, list):
                        # Azure Resource Graph structure: frontendIPConfigurations[0].properties.subnet.id
                        frontend_props = frontend_configs[0].get("properties", {})
                        subnet_ref = frontend_props.get("subnet", {})
                        subnet_id = subnet_ref.get("id", "") if isinstance(subnet_ref, dict) else ""
                        logger.debug(
                            f"LB {resource_name}: Azure Resource Graph subnet_id={subnet_id}"
                        )

            # Special handling for VMs - subnet is in network interface
            if not subnet_id and ("virtualmachine" in resource_type or "vm" in resource_type):
                # Get NIC ID from VM properties
                network_profile = properties.get("networkProfile", {})
                nic_refs = network_profile.get("networkInterfaces", [])
                logger.debug(
                    f"VM {resource_name}: network_profile={network_profile}, nic_refs={nic_refs}"
                )

                if nic_refs and isinstance(nic_refs, list):
                    # NIC ref can be either a dict with 'id' key or a string ID directly
                    nic_ref = nic_refs[0]
                    nic_id = nic_ref.get("id", "") if isinstance(nic_ref, dict) else nic_ref
                    logger.debug(f"VM {resource_name}: extracted nic_id={nic_id}")

                    if nic_id:
                        # Find the NIC resource and extract its subnet
                        nic_found = False
                        for nic_resource in resources:
                            nic_resource_id = nic_resource.get("id", "")
                            # Match full ID or check if NIC ID is contained in resource ID
                            if (
                                nic_resource_id == nic_id
                                or nic_id in nic_resource_id
                                or nic_resource_id in nic_id
                            ):
                                logger.debug(
                                    f"VM {resource_name}: found matching NIC {nic_resource_id}"
                                )
                                nic_found = True
                                nic_properties = nic_resource.get("properties", {})
                                ip_configs = nic_properties.get("ipConfigurations", [])
                                logger.debug(f"VM {resource_name}: NIC ip_configs={ip_configs}")
                                if ip_configs and isinstance(ip_configs, list):
                                    # Azure Resource Graph structure: ipConfigurations[0].properties.subnet.id
                                    ip_config_props = ip_configs[0].get("properties", {})
                                    subnet_ref = ip_config_props.get("subnet", {})
                                    subnet_id = (
                                        subnet_ref.get("id", "")
                                        if isinstance(subnet_ref, dict)
                                        else ""
                                    )
                                    logger.debug(
                                        f"VM {resource_name}: extracted subnet_id={subnet_id} from NIC"
                                    )
                                    break
                        if not nic_found:
                            logger.warning(
                                f"VM {resource_name}: NIC {nic_id} not found in resources list"
                            )

            # Special handling for NSGs - use naming convention to match subnet
            if not subnet_id and (
                "networksecuritygroup" in resource_type or "nsg" in resource_type
            ):
                logger.debug(f"NSG {resource_name}: attempting naming-based subnet matching")
                # NSG naming: "hub-vnet-mgmt-nsg" -> hub-vnet, mgmt subnet
                # or "f5-xc-ce-spoke-vnet-workload-nsg" -> f5-xc-ce-spoke-vnet, workload subnet

                # Common abbreviation mappings
                abbrev_map = {
                    "mgmt": "management",
                    "nva": "external",  # NVA typically in external/internet-facing subnet
                    "ext": "external",
                    "int": "internal",
                    "wl": "workload",
                }

                vnet_count = len(vnets)
                logger.debug(f"NSG {resource_name}: checking {vnet_count} VNets for match")

                for vnet_idx, vnet_name in enumerate(vnets, 1):
                    vnet_lower = vnet_name.lower()
                    logger.debug(
                        f"NSG {resource_name}: checking VNet {vnet_idx}/{vnet_count}: {vnet_name}"
                    )

                    # Check if resource name starts with vnet name
                    if resource_name.startswith(vnet_lower):
                        # Extract subnet hint from remaining name
                        remaining = resource_name[len(vnet_lower) :].strip("-")
                        # Remove 'nsg' suffix
                        remaining = remaining.replace("-nsg", "").replace("nsg", "").strip("-")

                        # Expand abbreviations
                        expanded = abbrev_map.get(remaining, remaining)

                        logger.debug(
                            f"NSG {resource_name}: matched VNet prefix {vnet_name}, "
                            f"remaining='{remaining}', expanded='{expanded}'"
                        )

                        # Match against subnet names
                        subnet_count = len(vnets[vnet_name]["subnets"])
                        logger.debug(
                            f"NSG {resource_name}: checking {subnet_count} subnets in VNet {vnet_name}"
                        )

                        for subnet_idx, subnet_name in enumerate(vnets[vnet_name]["subnets"], 1):
                            subnet_lower = subnet_name.lower()
                            logger.debug(
                                f"NSG {resource_name}: checking subnet {subnet_idx}/{subnet_count}: {subnet_name}"
                            )

                            # Check multiple matching strategies
                            if (
                                remaining in subnet_lower
                                or expanded in subnet_lower
                                or subnet_lower.endswith(remaining)
                                or subnet_lower.endswith(expanded)
                            ):
                                subnet_id = f"nsg_match_{vnet_name}_{subnet_name}"
                                logger.debug(
                                    f"NSG {resource_name}: matched to subnet {subnet_name} in VNet {vnet_name}"
                                )
                                break
                        if subnet_id:
                            logger.debug(
                                f"NSG {resource_name}: successfully matched, breaking VNet loop"
                            )
                            break
                    else:
                        logger.debug(
                            f"NSG {resource_name}: does not start with VNet prefix {vnet_name}"
                        )

                if not subnet_id:
                    logger.debug(f"NSG {resource_name}: no naming-based match found")

            # Special handling for route tables - use naming convention
            if not subnet_id and ("routetable" in resource_type or "route_table" in resource_type):
                logger.debug(
                    f"Route table {resource_name}: attempting naming-based subnet matching"
                )
                # Route table naming: "hub-vnet-rt" -> hub-vnet
                # or "f5-xc-ce-spoke-vnet-rt" -> f5-xc-ce-spoke-vnet

                vnet_count = len(vnets)
                logger.debug(f"Route table {resource_name}: checking {vnet_count} VNets for match")

                for vnet_idx, vnet_name in enumerate(vnets, 1):
                    vnet_lower = vnet_name.lower()
                    logger.debug(
                        f"Route table {resource_name}: checking VNet {vnet_idx}/{vnet_count}: {vnet_name}"
                    )

                    if vnet_lower in resource_name:
                        logger.debug(
                            f"Route table {resource_name}: matched VNet {vnet_name} in name"
                        )

                        # Assign to first non-gateway subnet in this vnet (typically default or workload)
                        subnet_count = len(vnets[vnet_name]["subnets"])
                        logger.debug(
                            f"Route table {resource_name}: checking {subnet_count} subnets in VNet {vnet_name}"
                        )

                        for subnet_idx, subnet_name in enumerate(vnets[vnet_name]["subnets"], 1):
                            logger.debug(
                                f"Route table {resource_name}: checking subnet {subnet_idx}/{subnet_count}: {subnet_name}"
                            )

                            if "gateway" not in subnet_name.lower():
                                subnet_id = f"rt_match_{vnet_name}_{subnet_name}"
                                logger.debug(
                                    f"Route table {resource_name}: matched to non-gateway subnet {subnet_name}"
                                )
                                break
                        if subnet_id:
                            logger.debug(
                                f"Route table {resource_name}: successfully matched, breaking VNet loop"
                            )
                            break
                    else:
                        logger.debug(
                            f"Route table {resource_name}: VNet name {vnet_name} not found in resource name"
                        )

                if not subnet_id:
                    logger.debug(f"Route table {resource_name}: no naming-based match found")

            # Try to match to a subnet
            assigned = False
            if subnet_id:
                logger.debug(
                    f"Resource {resource_name}: attempting subnet assignment with subnet_id={subnet_id}"
                )

                vnet_count = len(vnets)
                logger.debug(
                    f"Resource {resource_name}: checking {vnet_count} VNets for subnet assignment"
                )

                for vnet_idx, (vnet_name, vnet_data) in enumerate(vnets.items(), 1):
                    logger.debug(
                        f"Resource {resource_name}: checking VNet {vnet_idx}/{vnet_count}: {vnet_name}"
                    )

                    subnet_count = len(vnet_data["subnets"])
                    logger.debug(
                        f"Resource {resource_name}: checking {subnet_count} subnets in VNet {vnet_name}"
                    )

                    for subnet_idx, (subnet_name, subnet_data) in enumerate(
                        vnet_data["subnets"].items(), 1
                    ):
                        logger.debug(
                            f"Resource {resource_name}: checking subnet {subnet_idx}/{subnet_count}: {subnet_name}"
                        )

                        # Match by subnet ID (exact or contained)
                        # Check for exact match or if subnet ID is contained in resource's subnet_id (for Azure full paths)
                        if subnet_id == subnet_data["id"] or subnet_data["id"] in subnet_id:
                            logger.debug(
                                f"Resource {resource_name}: matched to subnet {subnet_name} (exact/contained match)"
                            )
                            subnet_data["resources"].append(resource)
                            assigned = True
                            break
                        # Check for naming-based match (NSG/route table convention)
                        elif subnet_id.startswith("nsg_match_") or subnet_id.startswith(
                            "rt_match_"
                        ):
                            parts = subnet_id.split("_")
                            if len(parts) >= 4:
                                matched_vnet = parts[2]
                                matched_subnet = "_".join(parts[3:])
                                logger.debug(
                                    f"Resource {resource_name}: checking naming match "
                                    f"vnet={matched_vnet}, subnet={matched_subnet}"
                                )

                                if vnet_name == matched_vnet and subnet_name == matched_subnet:
                                    logger.debug(
                                        f"Resource {resource_name}: matched to subnet {subnet_name} (naming match)"
                                    )
                                    subnet_data["resources"].append(resource)
                                    assigned = True
                                    break
                    if assigned:
                        logger.debug(
                            f"Resource {resource_name}: successfully assigned, breaking VNet loop"
                        )
                        break

                if not assigned:
                    logger.debug(
                        f"Resource {resource_name}: no subnet assignment match found with subnet_id"
                    )
            else:
                logger.debug(f"Resource {resource_name}: no subnet_id, skipping subnet assignment")

            # If not assigned to any subnet, try to infer VNet from resource name before fallback
            if not assigned and vnets:
                logger.debug(f"Resource {resource_name}: not assigned, attempting VNet inference")
                # Try to infer VNet from resource naming pattern
                inferred_vnet = None
                for vnet_name in vnets:
                    vnet_lower = vnet_name.lower()
                    # Check if VNet name is part of resource name
                    if vnet_lower in resource_name:
                        inferred_vnet = vnet_name
                        logger.debug(f"Resource {resource_name}: inferred VNet={vnet_name}")
                        break

                # Use inferred VNet if found, otherwise use first VNet
                default_vnet = inferred_vnet if inferred_vnet else list(vnets.keys())[0]
                logger.debug(f"Resource {resource_name}: using default VNet={default_vnet}")

                if "default-subnet" not in vnets[default_vnet]["subnets"]:
                    vnets[default_vnet]["subnets"]["default-subnet"] = {
                        "id": "default-subnet",
                        "address_prefix": "",
                        "resources": [],
                    }
                vnets[default_vnet]["subnets"]["default-subnet"]["resources"].append(resource)
                logger.debug(
                    f"Resource {resource_name}: assigned to default-subnet in {default_vnet}"
                )

            logger.debug(f"=== LOOP ITERATION {idx}/{len(resources)} END ===")

        logger.debug("Second pass complete: all resources assigned to subnets")
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

    def _add_internet_cloud(
        self, root: ET.Element, cell_id: int, hub_vnet_x: int = 700, hub_vnet_width: int = 850
    ) -> int:
        """
        Add Internet cloud shape at the top of the diagram, centered above hub VNet.
        Matches Microsoft Learn style with prominent cloud icon.

        Args:
            root: mxGraph root element
            cell_id: Current cell ID
            hub_vnet_x: X position of hub VNet (for centering)
            hub_vnet_width: Width of hub VNet (for centering calculation)

        Returns:
            Next available cell ID
        """
        cloud_id = str(cell_id)
        cell_id += 1

        # Center Internet cloud above hub VNet
        cloud_width = 200
        cloud_height = 100
        cloud_x = hub_vnet_x + (hub_vnet_width - cloud_width) // 2

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
            x=str(cloud_x),
            y="10",
            width=str(cloud_width),
            height=str(cloud_height),
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
            style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=12;fontColor=#0078D4;fontStyle=1;",
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
            style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=12;fontColor=#107C10;fontStyle=1;",
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

    def _export_to_svg(self, drawio_file: Path) -> Path:
        """
        Export .drawio file to SVG using drawio CLI.

        SVG format properly renders embedded base64 SVG icons,
        unlike PNG export which has limitations with embedded images.

        Args:
            drawio_file: Path to the .drawio file to export

        Returns:
            Path to the exported SVG file

        Raises:
            DiagramGenerationError: If SVG export fails
        """
        svg_file = drawio_file.with_suffix(".svg")

        try:
            # Use drawio CLI to export SVG
            # --export: export mode
            # --format svg: output format (preserves embedded SVG icons)
            # --transparent: transparent background
            # --border 10: add border around diagram
            # --crop: crop to diagram size
            subprocess.run(
                [
                    "drawio",
                    "--export",
                    "--format",
                    "svg",
                    "--transparent",
                    "--border",
                    "10",
                    "--crop",
                    "--output",
                    str(svg_file),
                    str(drawio_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("SVG export successful", svg_file=str(svg_file))
            return svg_file

        except subprocess.CalledProcessError as e:
            error_msg = f"SVG export failed: {e.stderr}"
            logger.error(error_msg, returncode=e.returncode)
            raise DiagramGenerationError(error_msg) from e
        except FileNotFoundError:
            error_msg = "drawio CLI not found. Install with: brew install --cask drawio"
            logger.error(error_msg)
            raise DiagramGenerationError(error_msg) from None
